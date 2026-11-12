"""Bounded primary-document collection without paid discovery searches.

Public state stores only URLs, hashes, cursors and outcomes. Raw sources and
model responses remain in ignored caches. Existing federal validators decide
whether each excerpt is admissible.
"""
import io
import json
import math
import re
import sys
import copy
import threading
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from contextlib import nullcontext
from difflib import SequenceMatcher
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
import policy_subjects

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts/daily'))
import federal
import federal_sources as sources
from scripts.federal_research import overlaps

VERSION = 1
AI = re.compile(r'\bartificial intelligence\b|\bAI\b|\bAGI\b|super[ -]?intelligence|frontier models?|machine learning|AI chips', re.I)
SELECTOR_VERSION = 2
STATE = 'data/federal_archive_state.json'
RAW = 'data/raw/federal_archives'


def remaining(baseline, limit, spent):
    if any(type(v) not in (float, int) or not math.isfinite(v) or v < 0 for v in (baseline, limit, spent)) or spent < baseline - 1e-6:
        raise ValueError('Invalid or regressed budget ledger')
    return max(0, limit - (spent - baseline))


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.href=None; self.label=[]
    def handle_starttag(self, tag, attrs):
        if tag=='a': self.href=dict(attrs).get('href'); self.label=[]
    def handle_data(self, data):
        if self.href: self.label.append(data)
    def handle_endtag(self, tag):
        if tag=='a' and self.href:
            self.links.append((self.href,sources.normalize(' '.join(self.label))));self.href=None


class FedArticle(HTMLParser):
    """Read the Fed's explicit article/speaker elements, excluding navigation."""
    def __init__(self):
        super().__init__();self.level=0;self.article=None;self.speaker=None;self.parts=[];self.names=[];self.name=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'):
            if self.article is not None:self.parts.append(' ')
            return
        self.level+=1
        if tag=='div' and attrs.get('id')=='article':self.article=self.level
        if self.article is not None:
            self.parts.append(' ')
            if tag=='p' and 'speaker' in attrs.get('class','').split():self.speaker=self.level;self.name=[]
    def handle_endtag(self,tag):
        if tag in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'):return
        if self.speaker==self.level:
            self.names.append(sources.normalize(''.join(self.name)));self.speaker=None
        if self.article==self.level:self.article=None
        if self.article is not None:self.parts.append(' ')
        self.level=max(0,self.level-1)
    def handle_data(self,data):
        if self.article is not None:self.parts.append(data)
        if self.speaker is not None:self.name.append(data)


class SECSpeaker(HTMLParser):
    """Read only commissioner links inside the SEC's explicit news-speaker field."""
    selector='div.field--name-dynamic-twig-fieldnode-news-speaker'
    def __init__(self):
        super().__init__();self.depth=0;self.field=None;self.link=False;self.parts=[];self.names=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='div':
            self.depth+=1
            if 'field--name-dynamic-twig-fieldnode-news-speaker' in attrs.get('class','').split():self.field=self.depth
        if tag=='a' and self.field is not None and re.fullmatch(r'/about/sec-commissioners/[^/]+',attrs.get('href','')):
            self.link=True;self.parts=[]
    def handle_endtag(self,tag):
        if tag=='a' and self.link:
            self.names.append(sources.normalize(''.join(self.parts)));self.link=False
        if tag=='div':
            if self.field==self.depth:self.field=None
            self.depth-=1
    def handle_data(self,data):
        if self.link:self.parts.append(data)


def sec_speech(url):
    parsed=urlsplit(url)
    return parsed.hostname=='www.sec.gov' and bool(re.fullmatch(r'/(?:newsroom/speeches-statements|news/speech)/[^/]+',parsed.path))


def archive_links(html, source):
    if source.get('format') == 'treasury_news_json':
        parsed=urlsplit(source['url'])
        if (parsed.scheme!='https' or parsed.netloc!='home.treasury.gov'
                or not re.fullmatch(r'/news-data/(press-releases|statements-remarks)/\d{4}-\d{4}\.json',parsed.path)):
            raise ValueError('Unsupported Treasury archive URL')
        payload=json.loads(html)
        if not isinstance(payload,dict) or not isinstance(payload.get('items'),list):
            raise ValueError('Invalid Treasury archive items')
        links=[]
        for row in payload['items']:
            if not isinstance(row,dict) or not isinstance(row.get('url'),str) or not isinstance(row.get('title'),str):continue
            stamp=row.get('date','')
            if not isinstance(stamp,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',stamp):continue
            try:date.fromisoformat(stamp)
            except ValueError:continue
            if stamp < source.get('since','0001-01-01'):continue
            links.append((row['url'],row['title']))
    else:
        parser=Links();parser.feed(html);links=parser.links
    found={}
    for href,title in links:
        url=sources.canonical_url(urljoin(source['url'],href))
        if sources.allowed_url(url,source['domains']) and re.search(source['pattern'],url):
            found[url]={'url':url,'title':title}
    return list(found.values())


def fetch(url, domains):
    """No paid fallback, cookies, credentials, or cross-domain redirect."""
    for _ in range(5):
        if not sources.allowed_url(url,domains):raise ValueError('Source outside configured domains')
        with httpx.stream('GET',url,timeout=30,follow_redirects=False,
                          headers={'User-Agent':'WashingtonAIResearch/1.0'}) as response:
            if response.is_redirect:
                url=urljoin(url,response.headers['location']);continue
            response.raise_for_status();parts=[];size=0
            for part in response.iter_bytes():
                size+=len(part)
                if size>12_000_000:raise ValueError('Source exceeds download limit')
                parts.append(part)
            return b''.join(parts),url
    raise ValueError('Source redirect limit')


def page_from_bytes(url, data, title=''):
    author=None;transcript={}
    if data.startswith(b'%PDF'):
        from pypdf import PdfReader
        text=' '.join(p.extract_text() or '' for p in PdfReader(io.BytesIO(data)).pages)
    else:
        html=data.decode('utf-8',errors='replace')
        parser=sources.PageText();parser.feed(html);text=''.join(parser.parts)
        transcript=sources.transcript_metadata(url,html)
        if urlsplit(url).hostname=='www.federalreserve.gov' and re.fullmatch(r'/newsevents/(speech|testimony)/[a-z]+\d{8}[a-z]\.htm',urlsplit(url).path):
            article=FedArticle();article.feed(html);body=sources.normalize(''.join(article.parts))
            if len(article.names)==1 and body in sources.normalize(text) and article.names[0] in body[:6000]:
                text=body
                author={'header':article.names[0],'selector':'div#article p.speaker','url':url}
        if sec_speech(url):
            speaker=SECSpeaker();speaker.feed(html)
            if len(speaker.names)==1 and speaker.names[0] in sources.normalize(text)[:6000]:
                author={'header':speaker.names[0],'selector':speaker.selector,'url':url}
    text=sources.normalize(text)
    if len(text)<120:raise ValueError('Insufficient source text')
    return {'url':url,'title':title,'text':text,'verified_via':'exact_normalized_page_text','parser_version':2,**transcript,**({'structured_author':author} if author else {})}


def extraction_signature(text, subjects, url='', title='', structured_author=None,model=None,transcript_lines=None):
    payload=[VERSION,sources.extraction_prompt(url),text,subjects,url,title,structured_author]
    if model is not None:payload.append({'model':model})
    if any(sources.bound_speakers(s,url) for s in subjects):
        payload.append({'speaker_context_version':sources.SPEAKER_CONTEXT_VERSION})
    if transcript_lines is not None:payload.append({'govinfo_pre_v1':sources.digest(transcript_lines)})
    return sources.digest(json.dumps(payload,sort_keys=True))


def duplicate_excerpt(statement, existing):
    key=policy_subjects.source_quote_key(statement)
    if key is not None and any(policy_subjects.source_quote_key(old)==key for old in existing):return True
    if overlaps(statement,existing):return True
    words=sources.normalize(statement['text']).casefold().split()
    for old in existing:
        if old.get('date')!=statement.get('date'):continue
        other=sources.normalize(old['text']).casefold().split()
        match=SequenceMatcher(None,words,other,autojunk=False).find_longest_match()
        if match.size>=8 and match.size>=0.5*min(len(words),len(other)):return True
    return False


def retained_attribution_context(root, subject_id, statement, page):
    """Verify immutable source offsets, or recover legacy source-bound proof."""
    span_hash=statement.get('attribution_span_sha256')
    if not span_hash:return statement.get('context')
    if 'attribution_span_start' in statement or 'attribution_span_end' in statement:
        text=sources.normalize(page['text']);start=statement.get('attribution_span_start');end=statement.get('attribution_span_end')
        if (type(start) is not int or type(end) is not int or not 0<=start<end<=len(text)
                or sources.digest(text)!=statement.get('source_text_sha256')
                or sources.digest(text[start:end])!=span_hash):
            raise ValueError('Reporting attribution source offsets or hashes changed')
        return text[start:end]
    root=Path(root)
    state=federal.read(root/STATE,{})
    signature=state.get('documents',{}).get(statement['url'],{}).get('processed',{}).get('signature','')
    if not re.fullmatch(r'[a-f0-9]{64}',signature):
        raise ValueError('Reporting attribution lacks its source extraction checkpoint')
    for path in sorted((root/RAW/'extractions').glob(f'{signature}-*.json')):
        if path.name.endswith('.response.json'):continue
        rows=federal.read(path,[])
        if not isinstance(rows,list):continue
        for row in rows:
            if not isinstance(row,dict) or row.get('subject_id')!=subject_id:continue
            if sources.normalize(row.get('quote',''))!=sources.normalize(statement['text']):continue
            context=sources.normalize(row.get('attribution_quote',''))
            if sources.digest(context)==span_hash:return context
    raise ValueError('Reporting attribution lacks an exact retained span hash match')


def process_document(root, page, subjects, state, client, max_chunks=30, *, take_chunk=None, evidence_lock=None):
    """Resume a document, reusing validated or rejected model outputs unchanged."""
    model=getattr(client,'model',None)
    text=sources.normalize(page['text']);signature=extraction_signature(text,subjects,page['url'],page.get('title',''),page.get('structured_author'),model,page.get('transcript_lines'))
    if state.get('signature')!=signature:state.clear();state.update(signature=signature,chunks={},model=model)
    report={'status':'complete','model_requests':0,'rejected':0,'extraction_errors':0,'added':{},'chunks_checked':0,'duplicate_excerpts':0}
    if page.get('verified_via') == 'exact_normalized_search_retrieval':
        state.update(status='needs_review',reason='full_source_snapshot_required',
                     source_text_sha256=sources.digest(text),selector_version=SELECTOR_VERSION)
        report.update(status='needs_review',reason='full_source_snapshot_required')
        return report
    if subjects and '/CHRG-' in page['url']:
        subjects=[s for s in subjects if any(page['url'] in alias.get('source_urls',[]) for alias in s.get('source_speaker_aliases',[]))]
        if not subjects:
            state.update(status='needs_review',reason='reviewed_speaker_mapping_required',source_text_sha256=sources.digest(text),selector_version=SELECTOR_VERSION)
            report.update(status='needs_review',reason='reviewed_speaker_mapping_required')
            return report
    chunks=state['chunks'];all_done=True
    for index,start in enumerate(range(0,len(text),22000)):
        key=str(index);chunk={**page,'text':text[start:start+26000],'document_header':text[:6000]}
        named=[s for s in subjects if federal.contains_name(chunk['text'],s,source_url=page['url']) or federal.contains_name(text[:6000],s,source_url=page['url'])]
        if not named or not AI.search(chunk['text']):
            chunks[key]={'status':'no_candidates','rejected':0};continue
        if chunks.get(key,{}).get('status')=='no_candidates':chunks.pop(key)
        if key in chunks:
            report['rejected']+=chunks[key].get('rejected',0)
            report['extraction_errors']+=bool(chunks[key].get('error'));continue
        if report['chunks_checked']>=max_chunks or (take_chunk is not None and not take_chunk()):all_done=False;continue
        cache=Path(root)/RAW/'extractions'/f'{signature}-{index}.json'
        try:
            if cache.exists():rows=federal.read(cache,[])
            else:
                response_cache=cache.with_suffix('.response.json')
                report['model_requests']+=not response_cache.exists()
                rows=client.extract(chunk,named,max_tokens=8000,response_cache=response_cache)
                federal.write(cache,rows)
            if not isinstance(rows,list):raise ValueError('Invalid extraction list')
            valid,rejected=federal.validate_rows(page,rows,named,federal.today())
            # Multi-speaker hearings require the existing reviewed speaker mapping.
            # A nearby name or a witness list is not enough to establish the speaker.
            if '/CHRG-' in page['url']:
                safe=[(pid,s) for pid,s in valid if s.get('attribution',{}).get('speaker_identity_source_url')]
                rejected+=len(valid)-len(safe);valid=safe
            for pid in sorted({pid for pid,_ in valid}):
                with evidence_lock if evidence_lock is not None else nullcontext():
                    existing=federal.read(Path(root)/'evidence'/f'{pid}.json',{'statements':[]})['statements'];novel=[]
                    for who,statement in valid:
                        if who!=pid:continue
                        if duplicate_excerpt(statement,existing+novel):report['duplicate_excerpts']+=1
                        else:novel.append({**statement,'origin':'federal_archive'})
                    added=federal.append_evidence(Path(root),pid,novel)
                if added:report['added'].setdefault(pid,[]).extend(added)
            chunks[key]={'status':'needs_review' if rejected else 'complete','rejected':rejected}
            report['rejected']+=rejected;report['chunks_checked']+=1
        except (ValueError,TypeError,KeyError) as exc:
            chunks[key]={'status':'needs_review','rejected':0,'error':type(exc).__name__}
            report['extraction_errors']+=1;report['chunks_checked']+=1
        except Exception as exc:
            state.update(status='pending',source_text_sha256=sources.digest(text))
            exc.archive_report=report
            raise
    report['status']='pending' if not all_done else 'needs_review' if report['rejected'] or report['extraction_errors'] else 'complete'
    state.update(status=report['status'],source_text_sha256=sources.digest(text),rejected=report['rejected'],selector_version=SELECTOR_VERSION)
    return report


def discover(root, config, subjects, state, *, now=None):
    """Read bounded archive indexes and reuse known hearing URLs; never search."""
    now=now or federal.today();documents=state.setdefault('documents',{});indexes=state.setdefault('indexes',{});errors=[]
    groups=federal.read(Path(root)/'config/federal_sources.json',{}).get('groups',[])
    by_org={oid:g['id'] for g in groups for oid in g['organization_ids']}
    def add(row,origin,group=None,pid=None,reported_domains=None):
        url=sources.canonical_url(row['url']);host=urlsplit(url).hostname or ''
        if not sources.allowed_url(url,[host]):return
        if not host.endswith(('.gov','.mil')) and not sources.allowed_url(url,reported_domains or []):return
        doc=documents.setdefault(url,{'url':url,'title':row.get('title',''),'discovered_from':origin})
        if group:doc.setdefault('group',group)
        if pid:doc['subject_ids']=sorted(set(doc.get('subject_ids',[])+[pid]))
    def fetch_index(source):
        signature=sources.digest(json.dumps(source,sort_keys=True))
        try:
            data,_=fetch(source['url'],source['domains'])
            html=data.decode('utf-8',errors='replace')
            if 'bm-verify=' in html or '__cf_chl' in html:
                return source,[],{'checked_on':now,'signature':signature,'status':'source_unavailable','error':'SourceAccessChallenge'}
            links=archive_links(html,source)
            return source,links,{'checked_on':now,'signature':signature,'links':len(links),'sha256':sources.digest(html),'status':'complete'}
        except Exception as exc:
            return source,[],{'checked_on':now,'signature':signature,'status':'source_unavailable','error':type(exc).__name__}
    with ThreadPoolExecutor(max_workers=max(1,min(config.get('index_workers',1),8))) as pool:
        pending=[s for s in config['indexes'] if indexes.get(s['url'],{}).get('checked_on')!=now
                 or indexes.get(s['url'],{}).get('signature')!=sources.digest(json.dumps(s,sort_keys=True))]
        for source,links,result in pool.map(fetch_index,pending):
            indexes[source['url']]=result
            for row in links:add(row,source['url'],source.get('group'),
                                 reported_domains=source['domains'] if source.get('source_type')=='reported_statement' else None)
            if result.get('error'):errors.append({'url':source['url'],'stage':'index','error':result['error']})
    # Existing official documents are shared inventory, not one paid search per person.
    selected={s['id'] for s in subjects}
    seed_map=federal.read(Path(root)/'config/federal_research_seeds.json',{}).get('subjects',{})
    for person in subjects:
        for row in seed_map.get(person['id'],[]):
            add(row,'existing_official_source_leads',by_org.get(person.get('organization_id')),person['id'])
    for person in policy_subjects.load_subjects(root):
        for row in policy_subjects.load_evidence(root,person):
            u=row.get('url','')
            if ((person['id'] in selected and row.get('source_type')=='official_statement') or
                    (config.get('include_institution_sources') and person['entity_type']=='institution'
                     and row.get('verified') is True) or
                    (config.get('include_hearing_inventory') and ('/CHRG-' in u or '-Wstate-' in u))):
                add(row,'existing_verified_source_inventory',by_org.get(person.get('organization_id')),person['id'] if person['id'] in selected else None)
    return errors


def fair_documents(documents,*,preferred_ids=None,preferred_domains=None):
    """Rotate source groups; preserve priority and oldest-attempt order within each."""
    documents=list(documents)
    if preferred_ids or preferred_domains:
        def preferred(d):return bool(set(d.get('subject_ids',[])) & set(preferred_ids or [])) or sources.allowed_url(d['url'],preferred_domains or [])
        return fair_documents(d for d in documents if preferred(d))+fair_documents(d for d in documents if not preferred(d))
    buckets=defaultdict(list)
    for doc in documents:
        group=doc.get('group') or urlsplit(doc['url']).hostname
        buckets[group].append(doc)
    def priority(doc):
        kind=0 if AI.search(doc.get('title','')) else 1 if '/testimony/' in doc['url'] else 2 if '/CHRG-' in doc['url'] else 3
        return (doc.get('processed',{}).get('status') in ('complete','needs_review'),kind,doc.get('last_attempt',''),doc['url'])
    queues={g:deque(sorted(rows,key=priority)) for g,rows in buckets.items()}
    order=sorted(queues,key=lambda g:(min(d.get('last_attempt','') for d in queues[g]),g))
    result=[]
    while any(queues.values()):
        for group in order:
            if queues[group]:result.append(queues[group].popleft())
    return result


def named_subjects(text,subjects,url):
    """Discard impossible ASCII names before the unchanged exact name matcher.

    Python's Unicode IGNORECASE also matches these four non-ASCII letters to
    ASCII letters. Preserve them in the token filter. Non-ASCII names bypass
    this filter entirely, as do source-specific reviewed speaker mappings.
    """
    words=set(re.findall(r'[a-z]+',text.translate(str.maketrans({'İ':'I','ı':'i','ſ':'s','K':'K'})).lower()))
    url=sources.canonical_url(url)
    result=[]
    for subject in subjects:
        names=[sources.normalize(n) for n in [subject['name'],*subject.get('aliases',[])]]
        possible=any(not n.isascii() or set(re.findall(r'[a-z]+',n.lower()))<=words for n in names)
        possible=possible or any(url in alias.get('source_urls',[]) for alias in subject.get('source_speaker_aliases',[]))
        if possible and federal.contains_name(text,subject,source_url=url):result.append(subject)
    return result


def collect(root, config, client, *, ids=None, max_documents=30, max_chunks=60, discover_sources=True, fetch_workers=1, extraction_workers=1, urls=None):
    if type(fetch_workers) is not int or not 1<=fetch_workers<=8:raise ValueError('fetch_workers must be 1–8')
    if type(extraction_workers) is not int or not 1<=extraction_workers<=8:raise ValueError('extraction_workers must be 1–8')
    root=Path(root);all_subjects=[s for s in policy_subjects.load_subjects(root) if s['branch']=='executive' and s['entity_type']=='person']
    if ids is not None and not set(ids)<={s['id'] for s in all_subjects}:raise ValueError('Unknown or excluded official')
    subjects=[s for s in all_subjects if ids is None or s['id'] in ids]
    state=federal.read(root/STATE,{'version':VERSION,'documents':{},'indexes':{}});now=federal.today()
    report={'date':now,'status':'complete','discovery_model_requests':0,'model_requests':0,'fetched':0,'cached_documents':0,'checked_documents':0,'chunks_checked':0,'added':{},'rejected':0,'extraction_errors':0,'duplicate_excerpts':0,'errors':[]}
    if discover_sources:report['errors'].extend(discover(root,config,subjects,state,now=now))
    federal.write(root/STATE,state)
    report.update(document_outcomes=[],groups={})
    wanted_urls=None if urls is None else set(urls)
    groups=federal.read(root/'config/federal_sources.json',{}).get('groups',[])
    organizations={s.get('organization_id') for s in subjects}
    domains=sorted({d for g in groups if organizations.intersection(g['organization_ids']) for d in g['domains']})
    ordered=fair_documents((d for u,d in state['documents'].items() if wanted_urls is None or u in wanted_urls),preferred_ids=ids,preferred_domains=domains if ids is not None else None);queue=[]
    # Resolve unchanged caches before submitting work; no model request is needed.
    for original in ordered:
        doc=copy.deepcopy(original);url=doc['url'];cache=root/RAW/'pages'/f'{sources.digest(url)}.json';processed=doc.setdefault('processed',{})
        recent=doc.get('fetched_on','0001-01-01')>(date.fromisoformat(now)-timedelta(days=config.get('recheck_days',7))).isoformat()
        # Preserve failed-source cooldowns across repeated commands.
        if doc.get('error') and doc['error'] not in ('BudgetExceeded','OpenRouterRequestError') and doc.get('last_attempt')==now:continue
        page=federal.read(cache,{}) if cache.exists() and recent else None
        if page and sec_speech(url) and page.get('parser_version')!=2:page=None
        if page and sources.govinfo_transcript(url) and any(sources.bound_speakers(s,url) for s in subjects) and page.get('transcript_format')!='govinfo_pre_v1':page=None
        if page:
            named=named_subjects(page['text'],subjects,url)
            if processed.get('selector_version')==SELECTOR_VERSION and processed.get('signature')==extraction_signature(sources.normalize(page['text']),named,url,page.get('title',''),page.get('structured_author'),getattr(client,'model',None),page.get('transcript_lines')) and processed.get('status') in ('complete','needs_review'):
                report['cached_documents']+=1;continue
        queue.append((doc,page))
        if len(queue)>=max_documents:break
    chunk_lock=threading.Lock();evidence_lock=threading.Lock();extract_slots=threading.Semaphore(extraction_workers);used_chunks=0
    def take_chunk():
        nonlocal used_chunks
        with chunk_lock:
            if used_chunks>=max_chunks:return False
            used_chunks+=1;return True
    class LimitedClient:
        model=getattr(client,'model',None)
        def extract(self,*args,**kwargs):
            with extract_slots:return client.extract(*args,**kwargs)
    def work(item):
        doc,page=item;url=doc['url'];processed=doc['processed'];fetched=0
        doc['last_attempt']=now
        print('archive document: '+url,flush=True)
        try:
            if page is None:
                host=urlsplit(url).hostname;data,final_url=fetch(url,[host]);page=page_from_bytes(url,data,doc.get('title',''));page['retrieved_url']=final_url
                federal.write(root/RAW/'pages'/f'{sources.digest(url)}.json',page);doc['fetched_on']=now;fetched=1
            named=named_subjects(page['text'],subjects,url)
            result=process_document(root,page,named,processed,LimitedClient(),max_chunks=max_chunks,take_chunk=take_chunk,evidence_lock=evidence_lock)
            doc.pop('error',None)
            return doc,result,fetched,None
        except Exception as exc:
            doc['error']=type(exc).__name__
            return doc,getattr(exc,'archive_report',{}),fetched,type(exc).__name__
    with ThreadPoolExecutor(max_workers=fetch_workers) as pool:
        remaining_queue=iter(queue);pending=set()
        def fill_slots():
            while len(pending)<fetch_workers and used_chunks<max_chunks and report['status']=='complete':
                item=next(remaining_queue,None)
                if item is None:break
                pending.add(pool.submit(work,item))
        fill_slots()
        while pending:
            finished,pending=wait(pending,return_when=FIRST_COMPLETED)
            for future in finished:
                doc,result,fetched,error=future.result();url=doc['url'];state['documents'][url]=doc
                report['checked_documents']+=1;report['fetched']+=fetched
                for key in ('model_requests','chunks_checked','rejected','extraction_errors','duplicate_excerpts'):report[key]+=result.get(key,0)
                for pid,sids in result.get('added',{}).items():report['added'].setdefault(pid,[]).extend(sids)
                group=doc.get('group') or urlsplit(url).hostname
                counts=report['groups'].setdefault(group,{'checked':0,'new_statements':0,'source_gaps':0})
                counts['checked']+=1;counts['new_statements']+=sum(map(len,result.get('added',{}).values()));counts['source_gaps']+=bool(error)
                report['document_outcomes'].append({'url':url,'group':group,'status':error or result.get('status'),'added':result.get('added',{})})
                if error:
                    report['errors'].append({'url':url,'stage':'document','error':error})
                    if error in ('BudgetExceeded','OpenRouterRequestError'):
                        report['status']='collection_budget_limit' if error=='BudgetExceeded' else 'provider_limit'
                federal.write(root/STATE,state)
            # A slow document must not leave completed workers idle. Keep the
            # same bounded in-flight work, shared chunk limit and budget client.
            fill_slots()
    report['inventory_documents']=len(state['documents'])
    report['remaining_documents']=sum(d.get('processed',{}).get('status') not in ('complete','needs_review') for d in state['documents'].values())
    report['review_documents']=sum(d.get('processed',{}).get('status')=='needs_review' for d in state['documents'].values())
    report['source_gap_documents']=sum(bool(d.get('error')) for d in state['documents'].values())
    report['source_gap_indexes']=sum(d.get('status')=='source_unavailable' for d in state['indexes'].values())
    report['new_statements']=sum(map(len,report['added'].values()))
    if report['status']=='complete' and (report['errors'] or report['remaining_documents'] or report['review_documents']):report['status']='partial'
    return report
