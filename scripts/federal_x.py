"""Resumable federal X search through the configured official API or emusks provider.

Usage: uv run python scripts/federal_x.py plan [--mode historical]
       uv run python scripts/federal_x.py collect --mode historical [--ids nsa,commerce]
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts/daily')]
import policy_subjects
from dotenv import dotenv_values
from federal_sources import digest
from federal_x_config import KEYWORDS, fingerprint, current_job, provider as configured_provider, state_file

AI=re.compile(r'\b(?:AI|AGI|artificial intelligence|superintelligence|super intelligence|OpenAI|Anthropic|export controls?|frontier act|kill switch act|stop stealing our chips|independent verification)\b',re.I)
ERRORS={'missing_auth_token','missing_bearer_token','authentication_failed','rate_limited','timeout','request_failed','malformed_response','budget_exceeded','credits_exhausted','account_identity_changed','account_unavailable','window_not_ready'}

def read(path, default):
    return json.loads(path.read_text()) if path.exists() else default

def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n')
    temporary.replace(path)

def windows(start, end):
    current=date.fromisoformat(start);last=date.fromisoformat(end);out=[]
    while current<last:
        following=date(current.year+(current.month==12),current.month%12+1,1)
        stop=min(last,following);out.append((current.isoformat(),stop.isoformat()));current=stop
    return out

def registry(root):
    config=read(root/'config/federal_x.json',{'version':1,'enabled':False,'accounts':[]})
    configured_provider(config)
    cost=config.get('api_max_cost',2)
    if isinstance(cost,bool) or not isinstance(cost,(int,float)) or not math.isfinite(cost) or cost<0:
        raise ValueError('Invalid X API cost limit')
    if config.get('historical_window','month') not in ('month','account'):
        raise ValueError('Invalid historical window')
    if config.get('historical_until'):date.fromisoformat(config['historical_until'])
    subjects={p['id']:p for p in policy_subjects.load_subjects(root) if p['branch']=='executive'}
    seen={};ids=set()
    for a in config['accounts']:
        p=subjects.get(a.get('subject_id'));handle=a.get('handle','')
        if (not p or not re.fullmatch(r'[A-Za-z0-9_]{1,15}',handle) or not re.fullmatch(r'[a-z0-9_]+',a.get('id','')) or a['id'] in ids):
            raise ValueError('Invalid or duplicate federal X account')
        ids.add(a['id'])
        source=urlsplit(a.get('source_url',''))
        if source.scheme!='https' or not source.hostname or not a.get('verified_on'):
            raise ValueError('X account needs a checked source')
        date.fromisoformat(a['verified_on'])
        start=date.fromisoformat(a['valid_from']);end=date.fromisoformat(a.get('valid_until') or '9999-12-31')
        if start>=end:raise ValueError('Invalid account interval')
        for other_start,other_end in seen.setdefault(handle.lower(),[]):
            if start<other_end and other_start<end:raise ValueError('Overlapping X account owners')
        seen[handle.lower()].append((start,end))
        if a['kind'] not in ('personal','official_role','institutional') or (a['kind']=='institutional')!=(p['entity_type']=='institution'):
            raise ValueError('X attribution does not match subject')
        if a['kind']=='official_role':
            index=a.get('role_index')
            if isinstance(index,bool) or not isinstance(index,int) or not 0<=index<len(p['roles']):
                raise ValueError('X account needs a sourced role')
    return config,subjects

def excerpt(text):
    """One contiguous excerpt, capped at 25 words, near the policy term."""
    words=list(re.finditer(r'\S+',text));match=AI.search(text)
    if not match or len(words)<8:return None
    pivot=next((i for i,w in enumerate(words) if w.end()>match.start()),0)
    start=max(0,min(pivot-5,len(words)-25));end=min(len(words),start+25)
    return text[words[start].start():words[end-1].end()]

def post_date(value):
    try:moment=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:moment=datetime.strptime(value,'%a %b %d %H:%M:%S %z %Y')
    if moment.tzinfo is None:raise ValueError('malformed_response')
    return moment.astimezone(timezone.utc).date().isoformat()

def valid_post(post):
    if not isinstance(post,dict):return False
    for field in ('id','author_id'):
        if not isinstance(post.get(field),str) or not re.fullmatch(r'\d+',post[field]):return False
    if not isinstance(post.get('text'),str) or not isinstance(post.get('author'),str) or not re.fullmatch(r'[A-Za-z0-9_]{1,15}',post['author']):return False
    if not all(isinstance(post.get(flag),bool) for flag in ('is_repost','is_promoted','restricted')):return False
    try:post_date(post['created_at'])
    except (KeyError,ValueError,TypeError,AttributeError):return False
    return True

def statement(post, account, subject, user_id, start, end, now, provider='emusks'):
    try:
        if (str(post['author_id'])!=str(user_id) or post['author'].lower()!=account['handle'].lower() or
            post.get('is_repost') or post.get('is_promoted') or post.get('restricted') or
            not re.fullmatch(r'\d+',post['id'])):return None
        raw_date=post['created_at']
        day=post_date(raw_date)
        if not start<=day<end or day>now or day<account['valid_from'] or (account.get('valid_until') and day>=account['valid_until']):return None
        text=post['text']
        if not isinstance(text,str) or not (quote:=excerpt(text)):return None
        attr={'kind':account['kind'],'speaker':subject['name'],'basis':'verified_x_account','account':account['handle'],'user_id':str(user_id)}
        if account['kind']=='institutional':attr['organization_id']=subject['organization_id']
        if account['kind']=='official_role':
            role=subject['roles'][account['role_index']]
            if (role.get('start_date') and day<role['start_date']) or (role.get('end_date') and day>role['end_date']):return None
            attr.update(organization_id=role['organization_id'],role=role['title'])
        return {'text':quote,'date':day,'date_quote':raw_date,'context':f"Original public X post by {subject['name']}.",
            'url':f"https://x.com/{account['handle']}/status/{post['id']}",'source_type':'x',
            'verified':True,'verified_via':provider+'_post_text_and_author_id','attribution':attr,
            'retrieved_on':now,'source_text_sha256':digest(text),'origin':'federal_x',
            'post_id':post['id'],'account_source_url':account['source_url'],
            'excerpted':quote!=text,'attribution_span_sha256':digest(str(user_id)+':'+post['author'])}
    except (KeyError,ValueError,TypeError,AttributeError):return None

def request_page(root, request):
    try:
        process=subprocess.run(['node',str(root/'scripts/federal_x_worker.mjs')],input=json.dumps(request),text=True,
            capture_output=True,cwd=root,timeout=70)
        result=json.loads(process.stdout)
        if not isinstance(result,dict):raise ValueError('Invalid response')
        return result
    except subprocess.TimeoutExpired:return {'error':'timeout'}
    except Exception:return {'error':'request_failed'}

def collect(root, mode='daily', since=None, dry=False, client=None, now=None, ids=None, page_limit=None):
    from federal import append_evidence
    root=Path(root);now=now or datetime.now(timezone.utc).date().isoformat();date.fromisoformat(now)
    config,subjects=registry(root)
    provider=configured_provider(config)
    if mode not in ('daily','historical'):raise ValueError('Unknown X collection mode')
    if since:
        date.fromisoformat(since)
        # Use the requested start for historical checkpoint selection too.
        if mode=='historical':config={**config,'since':since}
    accounts=[a for a in config['accounts'] if not ids or a['subject_id'] in ids]
    if ids and set(ids)-set(subjects):raise ValueError('Unknown federal profile')
    mapped={a['subject_id'] for a in config['accounts']}
    report={'date':now,'provider':provider,'mode':mode,'status':'dry_run' if dry else 'ok',
        'accounts':len({a['handle'].lower() for a in accounts}),'account_intervals':len(accounts),
        'mapped_profiles':len(mapped),'unmapped_profiles':len(subjects)-len(mapped),'pages':0,'added':{},'errors':[],
        'note':'Search results are not a complete X archive. Unmapped profiles need sourced account mappings.'}
    if not config.get('enabled'):return report|{'status':'disabled'}
    state_path=root/'data'/state_file(config);status_path=root/'data/federal_x_status.json'
    legacy=read(root/'data/federal_x_state.json',{}) if provider=='x_api' else {}
    state=read(state_path,{'version':1,'accounts':legacy.get('accounts',{}),'jobs':{},'last_request_at':0})
    end=(date.fromisoformat(now)+timedelta(days=1)).isoformat()
    # Historical and daily jobs have independent checkpoints.
    history_window=config.get('historical_window','month')
    if mode=='historical' and history_window=='account' and (not config.get('historical_until') or config['historical_until']>end):
        raise ValueError('Account history requires a fixed historical_until no later than tomorrow (exclusive)')
    jobs=[]
    active_fingerprints={a['id']:fingerprint(a) for a in accounts}
    for a in accounts:
        account_fingerprint=active_fingerprints[a['id']]
        previous=[j for j in state['jobs'].values() if j['account_id']==a['id'] and j['mode']==mode and current_job(j,active_fingerprints,config,end)]
        pending=sorted([j for j in previous if j['status']!='searched'],key=lambda j:j['start'])
        jobs.extend(pending)
        if mode=='daily':
            if not since and end in [j['end'] for j in previous]:continue
            prior_ends=[j['end'] for j in previous]
            start=since or ((date.fromisoformat(max(prior_ends))-timedelta(days=config.get('overlap_days',3))).isoformat() if prior_ends else
                            (date.fromisoformat(now)-timedelta(days=14)).isoformat())
            intervals=[(max(start,a['valid_from']),min(end,a.get('valid_until') or end))]
        else:
            start=max(since or config['since'],a['valid_from'])
            stop=min(end,a.get('valid_until') or end,config.get('historical_until') or end)
            intervals=[(start,stop)] if history_window=='account' else windows(start,stop)
        for start,stop in intervals:
            if start>=stop:continue
            key=digest(f'{account_fingerprint}:{mode}:{start}:{stop}'+(':account' if mode=='historical' and history_window=='account' else ''))
            existing=state['jobs'].get(key)
            if existing and existing['status']=='searched':continue
            jobs.append(existing or {'key':key,'account_id':a['id'],'fingerprint':account_fingerprint,'mode':mode,
                'start':start,'end':stop,'cursor':None,'status':'pending','pages':0,'last_attempt':0,
                'window':history_window if mode=='historical' else 'daily'})
    jobs=list({j['key']:j for j in jobs}.values())
    report['pending_windows']=len(jobs)
    if dry:return report
    auth_name='X_BEARER_TOKEN' if provider=='x_api' else 'X_AUTH_TOKEN'
    if client is None and not (os.environ.get(auth_name) or dotenv_values(root/'.env').get(auth_name)):
        report.update(status='unavailable',error='missing_bearer_token' if provider=='x_api' else 'missing_auth_token');write(status_path,report);return report
    if state.get('retry_after',0)>time.time():
        report.update(status='partial',error='rate_limited',retry_after=state['retry_after']);write(status_path,report);return report
    # An injected client is an offline transport; production always applies the global interval.
    if client is not None:
        transport=client
    elif provider=='x_api':
        from federal_x_api import Client
        transport=Client(root,state,max_cost=config.get('api_max_cost',2),daily=mode=='daily',checkpoint=lambda:write(state_path,state))
    else:
        transport=lambda req:request_page(root,req)
    deadline=time.monotonic()+config.get('max_seconds',720)
    limit=page_limit if page_limit is not None else config.get('page_limit',30)
    if not isinstance(limit,int) or not 1<=limit<=500:raise ValueError('X page limit must be between 1 and 500')
    by_id={a['id']:a for a in accounts}
    for job in jobs:state['jobs'][job['key']]=job
    write(state_path,state)
    while jobs and report['pages']<limit and time.monotonic()<deadline:
        jobs.sort(key=lambda j:(j.get('last_attempt',0),j['start'],j['account_id']))
        job=jobs.pop(0);a=by_id[job['account_id']]
        wait=max(0,state.get('last_request_at',0)+max(20,config.get('minimum_gap_seconds',20))-time.time()) if client is None and provider=='emusks' else 0
        if time.monotonic()+wait+70>deadline and client is None:jobs.insert(0,job);break
        if wait:time.sleep(wait)
        job['last_attempt']=time.time();state['last_request_at']=time.time();write(state_path,state)
        request={'handle':a['handle'],'query':f"from:{a['handle']} {KEYWORDS} since:{job['start']} until:{job['end']} -filter:retweets",'cursor':job['cursor']}
        try:
            if provider=='x_api':
                end_stamp=datetime.fromisoformat(job['end']).replace(tzinfo=timezone.utc).timestamp()
                latest=time.time()-60
                if mode=='historical' and end_stamp>latest:raise ValueError('window_not_ready')
                job.setdefault('query_end_time',datetime.fromtimestamp(min(end_stamp,latest),timezone.utc).isoformat().replace('+00:00','Z'))
                start_time=job['start']+'T00:00:00Z'
                if job['query_end_time']<=start_time:raise ValueError('window_not_ready')
                request.update(query=f"from:{a['handle']} {KEYWORDS} -is:retweet",start_time=start_time,end_time=job['query_end_time'])
                write(state_path,state)  # Freeze query dates before the first paid request.
            result=transport(request);report['pages']+=1
            if not isinstance(result,dict):raise ValueError('malformed_response')
            if result.get('error'):
                code=result['error'] if result['error'] in ERRORS else 'request_failed'
                if code=='rate_limited':state['retry_after']=max(state.get('retry_after',0),time.time()+15*60)
                raise ValueError(code)
            owner=result['account'];uid=owner['id']
            if not isinstance(uid,str) or not uid.isdigit() or owner['username'].lower()!=a['handle'].lower():raise ValueError('account_identity_changed')
            pinned=state['accounts'].get(a['id'],{}).get('user_id')
            if pinned and pinned!=uid:raise ValueError('account_identity_changed')
            state['accounts'][a['id']]={'user_id':uid,'handle':a['handle'],'resolved_on':now}
            posts=result['posts'];cursor=result.get('cursor')
            if not isinstance(posts,list) or not all(valid_post(p) for p in posts) or (cursor is not None and not isinstance(cursor,str)):raise ValueError('malformed_response')
            if cursor and (cursor==job['cursor'] or digest(cursor) in job.get('cursor_hashes',[])):raise ValueError('repeated_cursor')
            # Store the public provider response before appending evidence; replay remains idempotent.
            cache=root/'data/raw'/('federal_x_api' if provider=='x_api' else 'federal_x')/a['id']/(digest(json.dumps(request,sort_keys=True))+'.json')
            write(cache,{'request':request,'response':result,'retrieved_on':now})
            previous_posts={s.get('post_id') for s in read(root/'evidence'/f"{a['subject_id']}.json",{'statements':[]})['statements']}
            accepted=[s for p in posts if p.get('id') not in previous_posts and (s:=statement(p,a,subjects[a['subject_id']],uid,job['start'],job['end'],now,provider))]
            added=append_evidence(root,a['subject_id'],accepted)
            if added:report['added'].setdefault(a['subject_id'],[]).extend(added)
            job.update(cursor=cursor,pages=job['pages']+1,status='pending' if cursor else 'searched')
            if cursor:job.setdefault('cursor_hashes',[]).append(digest(cursor))
            job.pop('error',None)
            if cursor:jobs.append(job)
        except Exception as exc:
            code=str(exc) if isinstance(exc,ValueError) and str(exc) in ERRORS|{'repeated_cursor','account_identity_changed','malformed_response'} else 'request_failed'
            job.update(status='pending',error=code);report['errors'].append({'account_id':a['id'],'error':code})
            if code in ('rate_limited','authentication_failed','missing_auth_token','missing_bearer_token','budget_exceeded','credits_exhausted'):
                report['error']=code;write(state_path,state);break
            # A failed account waits until the next invocation instead of starving other accounts.
            jobs=[j for j in jobs if j['account_id']!=a['id']]
        write(state_path,state)
    report['pending_windows']=sum(j['status']!='searched' for j in state['jobs'].values()
        if j['mode']==mode and current_job(j,active_fingerprints,config,end))
    if report['pending_windows'] or report['errors']:report['status']='partial'
    if provider=='x_api' and client is None:report['estimated_cost_usd']=round(transport.spent,4)
    write(status_path,report);return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['plan','collect']);parser.add_argument('--mode',choices=['daily','historical'],default='daily')
    parser.add_argument('--since');parser.add_argument('--ids');parser.add_argument('--max-pages',type=int)
    args=parser.parse_args()
    report=collect(ROOT,mode=args.mode,since=args.since,dry=args.command=='plan',ids=args.ids.split(',') if args.ids else None,page_limit=args.max_pages)
    print(json.dumps(report,indent=2))
    return int(report['status'] in ('partial','unavailable'))

if __name__=='__main__':raise SystemExit(main())
