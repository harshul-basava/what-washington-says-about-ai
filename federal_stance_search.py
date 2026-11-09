"""Bounded discovery for the frozen cohort of missing federal AI overall stances.

X search saves public posts for later verification and Astra review. It never
publishes evidence, and an unverified account mention is only a source lead.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import federal_analysis as a

MANIFEST='data/federal_stance_search.json'
X_STATE='data/federal_stance_x_search.json'
RAW='data/raw/federal_stance_search'
AI='(AI OR "artificial intelligence" OR AGI OR superintelligence OR ChatGPT)'
OUTLOOK='(benefits OR risks OR future OR promise OR opportunity OR humanity OR economy OR prosperity OR jobs OR transform OR dangerous OR threat)'
ADDITIONAL='("machine learning" OR "language models" OR "artificial general intelligence" OR automation OR "AI opportunity" OR "AI safety")'


def search_jobs(subjects,accounts,until):
    jobs=[];mapped=set()
    for account in accounts:
        pid=account['subject_id']
        if pid not in subjects:continue
        start=max('2023-01-01',account['valid_from']);end=min(until,account.get('valid_until') or until)
        if start>=end:continue
        mapped.add(pid)
        for terms in (AI+' '+OUTLOOK,ADDITIONAL):
            jobs.append({'subject_id':pid,'kind':'account','account':account,
                'query':f"from:{account['handle']} {terms} -is:retweet",'start':start,'end':end})
    for pid,subject in subjects.items():
        if pid in mapped:continue
        # Mentions cannot establish ownership or be imported as the subject's own words.
        name=subject['name'].replace('"','')
        jobs.append({'subject_id':pid,'kind':'mention','query':f'"{name}" {AI} -is:retweet',
                     'start':'2023-01-01','end':until})
    return [{**j,'id':a.digest(j)[:20]} for j in jobs]


def collect_x(root,max_cost=2,max_pages=100):
    from scripts.federal_x import registry
    from scripts.federal_x_api import Client,POST_COST,APIError
    import llm
    root=Path(root);manifest=a.read(root/MANIFEST);config,subjects=registry(root)
    subjects={pid:s for pid,s in subjects.items() if pid in manifest['target_ids']}
    if set(subjects)!=set(manifest['target_ids']):raise ValueError('Search cohort is no longer eligible')
    until=manifest['created_at'][:10]
    jobs=search_jobs(subjects,config['accounts'],until)
    state=a.read(root/X_STATE,{'version':1,'until':until,'jobs':{}})
    raw=root/RAW/'x';raw.mkdir(parents=True,exist_ok=True)
    # Reuse pinned numeric identities, but retain separate search cursors and time bounds.
    api_state={'accounts':a.read(root/'data/federal_x_api_state.json',{}).get('accounts',{}),
               **state.get('api',{})}
    def checkpoint():
        state['api']={k:v for k,v in api_state.items() if k!='accounts'};a.write(root/X_STATE,state)
    client=Client(root,api_state,max_cost=max_cost,daily=False,checkpoint=checkpoint)
    before=len(llm.LEDGER.read_text().splitlines());pages=0;errors=[]
    try:
        for job in jobs:
            saved=state['jobs'].get(job['id'],{})
            if saved.get('status')=='complete':continue
            saved=state['jobs'].setdefault(job['id'],{**job,'pages':0,'posts':0,'status':'pending'})
            while pages<max_pages:
                params={'query':job['query'],'start_time':job['start']+'T00:00:00Z',
                    'end_time':job['end']+'T00:00:00Z','max_results':20,'sort_order':'recency',
                    'tweet.fields':'created_at,author_id,referenced_tweets,note_tweet,withheld,entities'}
                if saved.get('cursor'):params['next_token']=saved['cursor']
                try:
                    if job['kind']=='account':
                        owner=client.owner(job['account']['handle'])
                        saved['owner']=owner
                    else:owner=None
                    result=client.request('tweets/search/all',params,20,POST_COST)
                    posts=result.get('data',[]);meta=result.get('meta',{})
                    if meta.get('result_count')!=len(posts):raise ValueError('X result count mismatch')
                    if owner and any(p.get('author_id')!=owner['id'] for p in posts):
                        raise ValueError('X author mismatch')
                    cursor=meta.get('next_token')
                    if cursor is not None and (not isinstance(cursor,str) or not cursor):raise ValueError('Invalid cursor')
                    if cursor and cursor==saved.get('cursor'):raise ValueError('Repeated cursor')
                    for post in posts:
                        day=post.get('created_at','')[:10]
                        if not job['start']<=day<job['end']:raise ValueError('Post outside permitted interval')
                    path=raw/f"{job['id']}-{saved['pages']:04d}.json"
                    a.write(path,{'job':job,'owner':owner,'response':result,
                        'retrieved_at':datetime.now(timezone.utc).isoformat()})
                    saved['pages']+=1;saved['posts']+=len(posts);saved['cursor']=cursor
                    saved['status']='pending' if cursor else 'complete';saved.pop('error',None)
                    pages+=1;checkpoint()
                    print(job['subject_id'],job['kind'],len(posts),'posts',saved['status'],flush=True)
                    if not cursor:break
                except (APIError,ValueError) as exc:
                    saved['error']=str(exc);errors.append({'id':job['id'],'error':str(exc)});checkpoint()
                    if str(exc) in ('budget_exceeded','rate_limited','credits_exhausted','authentication_failed'):return
                    break
            if pages>=max_pages:break
    finally:
        state.update({'target_ids':manifest['target_ids'],'cost':round(state.get('cost',0)+client.spent,6),
            'pending_jobs':sum(state['jobs'].get(j['id'],{}).get('status')!='complete' for j in jobs),
            'planned_jobs':len(jobs),'last_errors':errors})
        checkpoint()
        a.write(raw/'state.json',state)
        (raw/'cost_delta.jsonl').write_text('\n'.join(llm.LEDGER.read_text().splitlines()[before:])+'\n')
        print(json.dumps({'pages':pages,'pending_jobs':state['pending_jobs'],'cost':client.spent,'errors':errors}),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['x-search']);args=p.parse_args()
    if args.command=='x-search':collect_x(ROOT)

if __name__=='__main__':main()
