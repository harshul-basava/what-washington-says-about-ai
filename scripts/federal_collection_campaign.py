"""Resume a fixed-budget federal archive campaign without repeated paid discovery."""
import argparse
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts/daily')]
import federal_archives as archive
import federal_analysis as analysis
import federal_analysis_models as models
import policy_subjects
from scripts.federal_expansion_runner import command, read, write, review_cohort

PATH='data/federal_collection_campaign.json'
CONFIG='config/federal_collection_campaign.json'


def initialize(root,config,subjects,evidence,spent,x_spent,ledger_offset):
    path=Path(root)/PATH;saved=read(path)
    if saved:
        if saved['limits']!={k:config[k] for k in ('limit_usd','trial_limit_usd','collection_limit_usd','x_limit_usd')}:
            raise ValueError('Saved campaign limits cannot reset or change')
        return saved
    saved={'version':1,'created_on':archive.federal.today(),'status':'in_progress','baseline':spent,
           'x_baseline':x_spent,'ledger_offset':ledger_offset,'ids':[s['id'] for s in subjects],
           'limits':{k:config[k] for k in ('limit_usd','trial_limit_usd','collection_limit_usd','x_limit_usd')},
           'initial_sids':{s['id']:[r['sid'] for r in evidence[s['id']]] for s in subjects},'phases':{},'added':{}}
    write(path,saved);return saved


def allowance(audit,phase,spent,available):
    limit=audit['limits']['trial_limit_usd'] if phase=='trial' else audit['limits']['limit_usd']
    return min(archive.remaining(audit['baseline'],limit,spent),max(0,available))


def recover_additions(root,audit):
    result={}
    for pid in audit['ids']:
        rows=read(Path(root)/'evidence'/f'{pid}.json').get('statements',[])
        sids=[s['sid'] for s in rows if s['sid'] not in audit['initial_sids'][pid]]
        if sids:result[pid]=sids
    return result


def verify_sources(root,audit):
    root=Path(root);count=0;urls=set()
    for pid,sids in audit['added'].items():
        rows=read(root/'evidence'/f'{pid}.json').get('statements',[])
        if len(sids)!=len(set(sids)):raise ValueError('Duplicate campaign statement IDs')
        for sid in sids:
            found=[s for s in rows if s['sid']==sid]
            if len(found)!=1:raise ValueError('Missing or duplicate campaign evidence')
            row=found[0]
            if row.get('source_type')=='x':
                # X has its own post/author verifier and retained raw API responses.
                matches=[]
                for file in (root/'data/raw/federal_x_api').glob('*/*.json'):
                    payload=read(file)
                    for post in payload.get('response',{}).get('posts',[]):
                        if str(post.get('id'))==row.get('post_id'):
                            matches.append(post)
                if not any(archive.sources.normalize(row['text']) in archive.sources.normalize(p.get('text','')) and str(p.get('author_id'))==str(row.get('attribution',{}).get('user_id')) for p in matches):
                    raise ValueError('X evidence lacks retained exact post and author proof')
            else:
                page=read(root/archive.RAW/'pages'/f"{archive.sources.digest(row['url'])}.json")
                text=archive.sources.normalize(page.get('text',''))
                if not row.get('verified') or not text or archive.sources.normalize(row['text']) not in text or row.get('source_text_sha256')!=archive.sources.digest(text):
                    raise ValueError('Campaign excerpt or source snapshot changed')
            count+=1;urls.add(row['url'])
    return {'verified_new_excerpts':count,'unique_sources':len(urls),'model_requests':0,'errors':[]}


def gap_queries(subjects,evidence,groups,ranking):
    by_org={oid:g for g in groups for oid in g['organization_ids']};buckets=defaultdict(list)
    for s in subjects:
        group=by_org.get(s['organization_id'])
        if group and len(evidence[s['id']])<3:buckets[group['id']].append(s)
    queries={}
    for gid,people in buckets.items():
        people.sort(key=lambda s:(ranking.get(s['id'],9999),len(evidence[s['id']]),s['id']))
        group=by_org[people[0]['organization_id']];rows=[]
        for start in range(0,len(people),2):
            pair=people[start:start+2];names=' OR '.join('"'+s['name']+'"' for s in pair)
            rows.append({'group':gid,'ids':[s['id'] for s in pair],'domains':group['domains'],
                         'query':f'({names}) artificial intelligence super intelligence AI policy speeches testimony interviews'})
        queries[gid]=deque(rows)
    result=[]
    while any(queries.values()):
        for gid in sorted(queries):
            if queries[gid]:result.append(queries[gid].popleft())
    return result


def collection_spend(root,audit):
    rows=Path(root,'data/cost_ledger.jsonl').read_text().splitlines()[audit['ledger_offset']:]
    return sum(r.get('cost',0) for line in rows if (r:=json.loads(line)).get('tag') in ('federal_extract','federal_search'))


def run(root,phase):
    import llm
    root=Path(root);config=read(root/CONFIG);subjects,evidence=analysis.inputs(root)
    subjects=[s for s in subjects if s['entity_type']=='person' and s['branch']=='executive']
    credit=command(root,'scripts/openrouter_credit_check.py','--required-credit=0',capture=True)
    start=llm.spent('openrouter');credit_available=credit['spendable_usd']
    audit=initialize(root,config,subjects,evidence,start,llm.spent('x'),len(llm.LEDGER.read_text().splitlines()))
    if not set(audit['ids'])<={s['id'] for s in subjects}:raise ValueError('Current roster changed; reconcile campaign scope before resuming')
    if phase=='expand' and audit['phases'].get('trial',{}).get('status')!='complete':raise ValueError('The trial must pass before expansion')
    part=audit['phases'].setdefault(phase,{'status':'in_progress','archive_batches':[],'queries':{}})
    ids=config['trial_ids'] if phase=='trial' else audit['ids']
    if not set(ids)<=set(audit['ids']):raise ValueError('Campaign includes an excluded official')
    def available():return allowance(audit,phase,llm.spent('openrouter'),credit_available-(llm.spent('openrouter')-start))
    def collect_available():
        limit=.4 if phase=='trial' else audit['limits']['collection_limit_usd']
        reserve=2.6 if phase=='trial' else 20
        return max(0,min(limit-collection_spend(root,audit),available()-reserve))
    def save():
        audit['added']=recover_additions(root,audit)
        audit['spent_usd']=round(llm.spent('openrouter')-audit['baseline'],6)
        audit['collection_spent_usd']=round(collection_spend(root,audit),6)
        audit['x_spent_usd']=round(llm.spent('x')-audit['x_baseline'],6)
        audit['remaining_usd']=round(archive.remaining(audit['baseline'],audit['limits']['limit_usd'],llm.spent('openrouter')),6)
        audit['new_statements']=sum(map(len,audit['added'].values()))
        audit['updated_on']=archive.federal.today();write(root/PATH,audit)
    def collect_batch(limit,urls=None):
        client=archive.sources.Client(root,collect_available(),daily=False,wait_for_capacity=True)
        return archive.collect(root,read(root/'config/federal_archives.json'),client,ids=ids,max_documents=limit,
             max_chunks=40 if phase=='trial' else 200,fetch_workers=8,extraction_workers=4,
             discover_sources=not part['archive_batches'] and urls is None,urls=urls)
    save()
    try:
        if available()<=0:raise ValueError('Campaign allowance is exhausted')
        if not part.get('archives_finished'):
            quota=config['trial_documents'] if phase=='trial' else config['archive_documents']
            count=sum(b['checked_documents'] for b in part['archive_batches'])
            while count<quota and collect_available()>0:
                if sum(map(len,recover_additions(root,audit).values()))>=config['archive_excerpt_limit']:break
                result=collect_batch(min(120,quota-count));part['archive_batches'].append(result);save()
                count+=result['checked_documents']
                if result['status']=='provider_limit':raise ValueError('Collection provider requires recovery')
                if not result['checked_documents'] or result['status']=='collection_budget_limit':break
            part['archives_finished']=True;save()
        if phase=='expand' and not part.get('gap_search_finished'):
            _,current=analysis.inputs(root);groups=read(root/'config/federal_sources.json')['groups']
            selection=read(root/'data/federal_roster_selection.json')
            rank={pid:i for i,pid in enumerate(selection.get('selected_new_ids',[]))}
            queries=gap_queries(subjects,current,groups,rank)[:config['gap_query_limit']]
            until=(date.fromisoformat(audit['created_on'])+timedelta(days=1)).isoformat()
            state=read(root/archive.STATE);new_urls={u for entry in part['queries'].values() for u in entry.get('urls',[])}
            for offset in range(0,len(queries),4):
                if collect_available()<=0 or sum(map(len,recover_additions(root,audit).values()))>=config['total_excerpt_limit']:break
                client=archive.sources.Client(root,collect_available(),daily=False,wait_for_capacity=True)
                work=[]
                for q in queries[offset:offset+4]:
                    key=archive.sources.digest(json.dumps([q,'2023-01-01',until],sort_keys=True))
                    if part['queries'].get(key,{}).get('status')=='complete':continue
                    work.append((key,q))
                def search(item):
                    key,q=item
                    try:return key,q,client.search(q['query'],q['domains'],'2023-01-01',until=until),None
                    except Exception as exc:return key,q,[],type(exc).__name__
                with ThreadPoolExecutor(max_workers=4) as pool:
                    for key,q,pages,error in pool.map(search,work):
                        entry={'ids':q['ids'],'group':q['group'],'query':q['query'],'since':'2023-01-01','until':until,'status':'pending' if error else 'complete','urls':[]}
                        if error:entry['error']=error
                        for lead in pages:
                            url=lead['url'];entry['urls'].append(url);new_urls.add(url)
                            doc=state.setdefault('documents',{}).setdefault(url,{'url':url,'title':lead.get('title',''),'group':q['group'],'discovered_from':'campaign_gap_search'})
                            cache=root/archive.RAW/'pages'/f'{archive.sources.digest(url)}.json'
                            if cache.exists():continue
                            try:
                                page=client.page(lead,q['domains']);write(cache,page);doc['fetched_on']=archive.federal.today()
                            except Exception as exc:entry.setdefault('source_gaps',[]).append({'url':url,'error':type(exc).__name__})
                        part['queries'][key]=entry;write(root/archive.STATE,state);save()
                # Extract these shared documents once for all eligible named officials.
                if new_urls and collect_available()>0:
                    result=collect_batch(len(new_urls),urls=sorted(new_urls));part.setdefault('gap_batches',[]).append(result)
                    state=read(root/archive.STATE);new_urls.clear();save()
                    if result['status']=='provider_limit':raise ValueError('Gap extraction provider requires recovery')
            part['gap_search_finished']=True;save()
        if phase=='expand' and not part.get('x_finished'):
            from scripts import federal_x
            x_config,_=federal_x.registry(root);_,current=analysis.inputs(root)
            mapped={a['subject_id'] for a in x_config['accounts']}
            x_ids=[s['id'] for s in subjects if s['id'] in mapped and len(current[s['id']])<3]
            part['x_plan']=federal_x.collect(root,mode='historical',ids=x_ids,dry=True) if x_ids else {'pending_windows':0,'accounts':0}
            # Resume existing historical intervals. Do not create a new cutoff that
            # would repeat each account's previously completed history.
            x_available=archive.remaining(audit['x_baseline'],audit['limits']['x_limit_usd'],llm.spent('x'))
            if part['x_plan']['pending_windows'] and x_available>1:
                part['x']=federal_x.collect(root,mode='historical',ids=x_ids,page_limit=10,max_cost=min(2,x_available-1))
            part['x_finished']=True;save()
        # Only the new or changed evidence enters ordinary judgment jobs. Existing
        # regulation/summary caches invalidate when their complete profile changes.
        changed=sorted(recover_additions(root,audit))
        if phase=='trial' and not changed:raise ValueError('Trial has no new verified evidence; inspect sources before expansion')
        if changed:
            part['analysis']=models.run(root,max_cost=available(),workers=4,review_workers=2,ids=changed,build_output=False)
            save()
            if part['analysis']['status']!='ok':raise ValueError('Ordinary analysis remains pending')
            code=command(root,'scripts/phase3_policies.py','label','--scope','executive','--ids',','.join(changed),'--workers',2,'--max-cost',available(),'--defer-build')
            part['policies']=command(root,'scripts/phase3_policies.py','plan','--scope','executive','--ids',','.join(changed),capture=True);save()
            if code or part['policies']['uncached_requests']:raise ValueError('Policy judgments remain pending')
            part['astra']=review_cohort(root,'efficient_campaign',changed,available,2,set(changed),allow_x_context=True,build_output=False,
                                       x_allowance=lambda:archive.remaining(audit['x_baseline'],audit['limits']['x_limit_usd'],llm.spent('x')),reuse_existing=True)
            save()
            if part['astra']['status']!='complete':raise ValueError('Independent Astra review remains pending')
        part['verification']=verify_sources(root,audit)
        part['status']='complete';part.pop('error',None)
        audit['status']='complete' if phase=='expand' else 'trial_complete'
        save()
    except Exception as exc:
        part.update(status='pending',error=type(exc).__name__+': '+str(exc)[:160]);audit['status']='pending';raise
    finally:save()
    return audit


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['plan','run','verify']);p.add_argument('--phase',choices=['trial','expand'],default='trial');args=p.parse_args()
    if args.command=='run':result=run(ROOT,args.phase)
    elif args.command=='verify':result=verify_sources(ROOT,read(ROOT/PATH));write(ROOT/'data/federal_collection_verification.json',result)
    else:
        subjects,evidence=analysis.inputs(ROOT);config=read(ROOT/CONFIG)
        officials=[s for s in subjects if s['entity_type']=='person' and s['branch']=='executive']
        result={'officials':len(officials),'existing_statements':sum(len(evidence[s['id']]) for s in officials),
                'limits':config,'saved_progress':read(ROOT/PATH).get('status'),'paid_calls':0}
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
