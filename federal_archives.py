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
AI = re.compile(r'\bartificial intelligence\b|\bAI\b|\bAGI\b|superintelligence|frontier models?|machine learning|AI chips', re.I)
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


def archive_links(html, source):
    parser=Links();parser.feed(html);found={}
    for href,title in parser.links:
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
    author=None
    if data.startswith(b'%PDF'):
        from pypdf import PdfReader
        text=' '.join(p.extract_text() or '' for p in PdfReader(io.BytesIO(data)).pages)
    else:
        html=data.decode('utf-8',errors='replace')
        parser=sources.PageText();parser.feed(html);text=''.join(parser.parts)
        if urlsplit(url).hostname=='www.federalreserve.gov' and re.fullmatch(r'/newsevents/(speech|testimony)/[a-z]+\d{8}[a-z]\.htm',urlsplit(url).path):
            article=FedArticle();article.feed(html);body=sources.normalize(''.join(article.parts))
            if len(article.names)==1 and body in sources.normalize(text) and article.names[0] in body[:6000]:
                text=body
                author={'header':article.names[0],'selector':'div#article p.speaker','url':url}
    text=sources.normalize(text)
    if len(text)<120:raise ValueError('Insufficient source text')
    return {'url':url,'title':title,'text':text,'verified_via':'exact_normalized_page_text',**({'structured_author':author} if author else {})}


def extraction_signature(text, subjects, url='', title='', structured_author=None):
    return sources.digest(json.dumps([VERSION,sources.EXTRACTION_PROMPT,text,subjects,url,title,structured_author],sort_keys=True))


def duplicate_excerpt(statement, existing):
    if overlaps(statement,existing):return True
    words=sources.normalize(statement['text']).casefold().split()
    for old in existing:
        if old.get('date')!=statement.get('date'):continue
        other=sources.normalize(old['text']).casefold().split()
        match=SequenceMatcher(None,words,other,autojunk=False).find_longest_match()
        if match.size>=8 and match.size>=0.5*min(len(words),len(other)):return True
    return False


def process_document(root, page, subjects, state, client, max_chunks=30):
    """Resume a document, reusing validated or rejected model outputs unchanged."""
    text=sources.normalize(page['text']);signature=extraction_signature(text,subjects,page['url'],page.get('title',''),page.get('structured_author'))
    if state.get('signature')!=signature:state.clear();state.update(signature=signature,chunks={})
    report={'status':'complete','model_requests':0,'rejected':0,'extraction_errors':0,'added':{},'chunks_checked':0,'duplicate_excerpts':0}
    chunks=state['chunks'];all_done=True
    for index,start in enumerate(range(0,len(text),22000)):
        key=str(index);chunk={**page,'text':text[start:start+26000],'document_header':text[:6000]}
        named=[s for s in subjects if federal.contains_name(chunk['text'],s,source_url=page['url']) or federal.contains_name(text[:6000],s,source_url=page['url'])]
        if not named or not AI.search(chunk['text']):
            chunks[key]={'status':'no_candidates','rejected':0};continue
        if key in chunks:
            report['rejected']+=chunks[key].get('rejected',0)
            report['extraction_errors']+=bool(chunks[key].get('error'));continue
        if report['chunks_checked']>=max_chunks:all_done=False;continue
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
        except Exception:
            state.update(status='pending',source_text_sha256=sources.digest(text))
            raise
    report['status']='pending' if not all_done else 'needs_review' if report['rejected'] or report['extraction_errors'] else 'complete'
    state.update(status=report['status'],source_text_sha256=sources.digest(text),rejected=report['rejected'])
    return report


def discover(root, config, subjects, state, *, now=None):
    """Read bounded archive indexes and reuse known hearing URLs; never search."""
    now=now or federal.today();documents=state.setdefault('documents',{});indexes=state.setdefault('indexes',{});errors=[]
    def add(row,origin):
        url=sources.canonical_url(row['url']);host=urlsplit(url).hostname or ''
        if not host.endswith(('.gov','.mil')) or not sources.allowed_url(url,[host]):return
        documents.setdefault(url,{'url':url,'title':row.get('title',''),'discovered_from':origin})
    for source in config['indexes']:
        previous=indexes.get(source['url'],{})
        if previous.get('checked_on')==now:continue
        try:
            data,_=fetch(source['url'],source['domains'])
            links=archive_links(data.decode('utf-8',errors='replace'),source)
            for row in links:add(row,source['url'])
            indexes[source['url']]={'checked_on':now,'links':len(links),'sha256':sources.digest(data.decode('utf-8',errors='replace')),'status':'complete'}
        except Exception as exc:
            indexes[source['url']]={'checked_on':now,'status':'source_unavailable','error':type(exc).__name__}
            errors.append({'url':source['url'],'stage':'index','error':type(exc).__name__})
    # Existing official documents are shared inventory, not one paid search per person.
    selected={s['id'] for s in subjects}
    for person in policy_subjects.load_subjects(root):
        for row in policy_subjects.load_evidence(root,person):
            u=row.get('url','')
            if ((person['id'] in selected and row.get('source_type')=='official_statement') or
                    (config.get('include_hearing_inventory') and ('/CHRG-' in u or '-Wstate-' in u))):
                add(row,'existing_verified_source_inventory')
    return errors


def collect(root, config, client, *, ids=None, max_documents=30, max_chunks=60, discover_sources=True):
    root=Path(root);all_subjects=[s for s in policy_subjects.load_subjects(root) if s['branch']=='executive' and s['entity_type']=='person']
    if ids is not None and not set(ids)<={s['id'] for s in all_subjects}:raise ValueError('Unknown or excluded official')
    subjects=[s for s in all_subjects if ids is None or s['id'] in ids]
    state=federal.read(root/STATE,{'version':VERSION,'documents':{},'indexes':{}});now=federal.today()
    report={'date':now,'status':'complete','discovery_model_requests':0,'model_requests':0,'fetched':0,'cached_documents':0,'checked_documents':0,'chunks_checked':0,'added':{},'rejected':0,'extraction_errors':0,'duplicate_excerpts':0,'errors':[]}
    if discover_sources:report['errors'].extend(discover(root,config,subjects,state,now=now))
    federal.write(root/STATE,state)
    def priority(doc):
        kind=0 if AI.search(doc.get('title','')) else 1 if '/testimony/' in doc['url'] else 2 if '/CHRG-' in doc['url'] else 3
        return (doc.get('processed',{}).get('status') in ('complete','needs_review'),kind,doc.get('last_attempt',''),doc['url'])
    ordered=sorted(state['documents'].values(),key=priority)
    for doc in ordered:
        if report['checked_documents']>=max_documents or report['chunks_checked']>=max_chunks:break
        url=doc['url'];cache=root/RAW/'pages'/f'{sources.digest(url)}.json';processed=doc.setdefault('processed',{})
        recent=doc.get('fetched_on','0001-01-01')>(date.fromisoformat(now)-timedelta(days=config.get('recheck_days',7))).isoformat()
        # Preserve failed-source cooldowns across repeated commands.
        if doc.get('error') and doc['error'] not in ('BudgetExceeded','OpenRouterRequestError') and doc.get('last_attempt')==now:continue
        try:
            page=None
            if cache.exists() and recent:
                page=federal.read(cache,{})
                named=[s for s in subjects if federal.contains_name(page['text'],s,source_url=url)]
                if processed.get('signature')==extraction_signature(sources.normalize(page['text']),named,url,page.get('title',''),page.get('structured_author')) and processed.get('status') in ('complete','needs_review'):
                    report['cached_documents']+=1;continue
            doc['last_attempt']=now;report['checked_documents']+=1
            print(f"archive document {report['checked_documents']}/{max_documents}: {url}",flush=True)
            if page is None:
                host=urlsplit(url).hostname;data,final_url=fetch(url,[host]);page=page_from_bytes(url,data,doc.get('title',''));page['retrieved_url']=final_url
                federal.write(cache,page);doc['fetched_on']=now;report['fetched']+=1
            named=[s for s in subjects if federal.contains_name(page['text'],s,source_url=url)]
            result=process_document(root,page,named,processed,client,max_chunks=max_chunks-report['chunks_checked'])
            for k in ('model_requests','chunks_checked','rejected','extraction_errors','duplicate_excerpts'):report[k]+=result[k]
            for pid,sids in result['added'].items():report['added'].setdefault(pid,[]).extend(sids)
            doc.pop('error',None)
        except Exception as exc:
            doc.update(last_attempt=now,error=type(exc).__name__);report['errors'].append({'url':url,'stage':'document','error':type(exc).__name__})
            if type(exc).__name__ in ('BudgetExceeded','OpenRouterRequestError'):
                report['status']='collection_budget_limit' if type(exc).__name__=='BudgetExceeded' else 'provider_limit'
                federal.write(root/STATE,state);break
        finally:federal.write(root/STATE,state)
    report['inventory_documents']=len(state['documents'])
    report['remaining_documents']=sum(d.get('processed',{}).get('status') not in ('complete','needs_review') for d in state['documents'].values())
    report['review_documents']=sum(d.get('processed',{}).get('status')=='needs_review' for d in state['documents'].values())
    report['source_gap_documents']=sum(bool(d.get('error')) for d in state['documents'].values())
    report['source_gap_indexes']=sum(d.get('status')=='source_unavailable' for d in state['indexes'].values())
    report['new_statements']=sum(map(len,report['added'].values()))
    if report['status']=='complete' and (report['errors'] or report['remaining_documents'] or report['review_documents']):report['status']='partial'
    return report
