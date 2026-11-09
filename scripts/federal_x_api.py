"""Official X full-archive transport with bounded read costs and redacted failures."""
import math
import os
import re
import time
import uuid
from datetime import datetime

import httpx
from dotenv import dotenv_values

import llm
from federal_x_config import PROBLEM_TYPES

POST_COST=0.005
USER_COST=0.010
GAP=3.1  # Below 300 requests per 15 minutes, including account lookups.


class APIError(Exception):
    def __init__(self,code,diagnostic=None,problem_types=None):
        super().__init__(code)
        self.diagnostic=diagnostic
        self.problem_types=problem_types


class Client:
    def __init__(self,root,state,max_cost=2,daily=True,get=None,checkpoint=None):
        if isinstance(max_cost,bool) or not isinstance(max_cost,(int,float)) or not math.isfinite(max_cost) or max_cost<0:
            raise ValueError('Invalid X API cost limit')
        self.token=os.environ.get('X_BEARER_TOKEN') or dotenv_values(root/'.env').get('X_BEARER_TOKEN')
        if not self.token:raise ValueError('missing_bearer_token')
        self.state=state;self.max_cost=max_cost;self.daily=daily;self.spent=0.0
        self.get=get or httpx.get
        self.checkpoint=checkpoint or (lambda:None)
        self.accounts={}

    def available(self):
        limits=[self.max_cost-self.spent,llm.BUDGETS['x']-llm.spent('x')]
        if self.daily:
            limits.append(llm.BUDGETS.get('monthly',{}).get('x',float('inf'))-llm.spent_this_month('x'))
        return max(0,min(limits))

    def charge(self,path,cost,metadata):
        tag=('daily_' if self.daily else '')+'federal_x_api_'+('search' if path=='tweets/search/all' else 'lookup')
        llm._log('x',cost,tag,{'path':path,**metadata})
        self.spent+=cost

    def request(self,path,params,maximum,unit):
        if self.available()+1e-9<maximum*unit:raise APIError('budget_exceeded')
        if self.state.get('retry_after',0)>time.time():raise APIError('rate_limited')
        wait=max(0,self.state.get('api_next_request_at',0)-time.time())
        if wait>GAP+1:raise APIError('rate_limited')
        if wait:time.sleep(wait)
        self.state['api_next_request_at']=time.time()+GAP
        self.checkpoint()
        # Reserve before HTTP so an interrupted process cannot forget a billed read.
        reservation={'request_id':uuid.uuid4().hex,'ts':time.time()}
        reserved=maximum*unit
        self.charge(path,reserved,reservation|{'phase':'reservation','n':maximum,'cost_uncertain':True})
        def reconcile(count):
            # Append an adjustment; preserve both the audit trail and reservation month.
            self.charge(path,count*unit-reserved,reservation|{'phase':'reconciliation','n':count,'cost_uncertain':False})
        try:
            response=self.get('https://api.x.com/2/'+path,params=params,
                              headers={'Authorization':'Bearer '+self.token},timeout=30,follow_redirects=False)
        except (httpx.TimeoutException,httpx.TransportError) as exc:
            # Keep the existing reservation when the response is lost.
            raise APIError('timeout' if isinstance(exc,httpx.TimeoutException) else 'request_failed') from None
        if response.status_code==429 or response.headers.get('x-rate-limit-remaining')=='0':
            try:reset=float(response.headers['x-rate-limit-reset'])+1
            except (KeyError,TypeError,ValueError):reset=time.time()+900
            if not math.isfinite(reset):reset=time.time()+900
            self.state['retry_after']=max(time.time()+1,reset)
            self.checkpoint()
        if response.status_code in (401,403,402,429):reconcile(0)
        if response.status_code in (401,403):raise APIError('authentication_failed')
        if response.status_code==402:raise APIError('credits_exhausted')
        if response.status_code==429:raise APIError('rate_limited')
        if response.status_code!=200:raise APIError('request_failed')
        try:
            data=response.json()
            if not isinstance(data,dict):raise ValueError()
            resources=data.get('data',[] if path=='tweets/search/all' else None)
            if path=='tweets/search/all':
                if not isinstance(resources,list):raise ValueError()
                count=len(resources)
            else:
                if resources is not None and not isinstance(resources,dict):raise ValueError()
                count=int(resources is not None)
        except (ValueError,TypeError):
            raise APIError('malformed_response') from None
        reconcile(count)
        stage='search' if path=='tweets/search/all' else 'lookup'
        if data.get('errors'):
            allowed={prefix+kind:kind for prefix in ('https://api.x.com/2/problems/',
                'https://api.twitter.com/2/problems/') for kind in PROBLEM_TYPES}
            errors=data['errors'] if isinstance(data['errors'],list) else []
            kinds=sorted({allowed[e['type']] for e in errors if isinstance(e,dict)
                and isinstance(e.get('type'),str) and e['type'] in allowed})
            raise APIError('malformed_response',stage+'_response_errors',kinds)
        if count>maximum:raise APIError('malformed_response','response_count_invalid')
        return data

    def owner(self,handle):
        if handle.lower() in self.accounts:return self.accounts[handle.lower()]
        if self.available()+1e-9<USER_COST+10*POST_COST:raise APIError('budget_exceeded')
        owner=self.request('users/by/username/'+handle,{'user.fields':'protected,withheld'},1,USER_COST).get('data')
        if (not isinstance(owner,dict) or not isinstance(owner.get('id'),str) or not re.fullmatch(r'\d+',owner['id'])
                or not isinstance(owner.get('username'),str) or owner['username'].lower()!=handle.lower()):
            raise APIError('malformed_response','lookup_identity_invalid')
        if owner.get('protected') is not False or owner.get('withheld'):raise APIError('account_unavailable')
        pinned=[a['user_id'] for a in self.state.get('accounts',{}).values()
                if a.get('handle','').lower()==handle.lower() and a.get('user_id')]
        if any(uid!=owner['id'] for uid in pinned):raise APIError('account_identity_changed')
        self.accounts[handle.lower()]={'id':owner['id'],'username':owner['username']}
        return self.accounts[handle.lower()]

    def __call__(self,request):
        stage='lookup'
        try:
            handle=request['handle']
            if not isinstance(handle,str) or not re.fullmatch(r'[A-Za-z0-9_]{1,15}',handle):raise APIError('malformed_response')
            if self.state.get('retry_after',0)>time.time():raise APIError('rate_limited')
            owner=self.owner(handle)
            stage='search'
            maximum=min(500,math.floor((self.available()+1e-9)/POST_COST))
            if maximum<10:raise APIError('budget_exceeded')
            params={'query':request['query'],'start_time':request['start_time'],'end_time':request['end_time'],
                    'max_results':maximum,'sort_order':'recency',
                    'tweet.fields':'created_at,author_id,referenced_tweets,note_tweet,withheld'}
            if request.get('cursor'):params['next_token']=request['cursor']
            data=self.request('tweets/search/all',params,maximum,POST_COST)
            posts=data.get('data',[]);meta=data.get('meta',{})
            if not isinstance(meta,dict) or type(meta.get('result_count')) is not int or meta['result_count']!=len(posts):
                raise APIError('malformed_response','search_metadata_invalid')
            cursor=meta.get('next_token')
            if cursor is not None and (not isinstance(cursor,str) or not 0<len(cursor)<=10000):raise APIError('malformed_response','search_cursor_invalid')
            normalized=[]
            stage='post'
            for post in posts:
                if (not isinstance(post,dict) or not isinstance(post.get('id'),str) or not re.fullmatch(r'\d+',post['id'])
                        or post.get('author_id')!=owner['id']):raise APIError('malformed_response','post_identity_invalid')
                text=(post.get('note_post') or post.get('note_tweet') or {}).get('text') or post['text']
                if not isinstance(text,str) or not text:raise APIError('malformed_response','post_text_invalid')
                moment=datetime.fromisoformat(post['created_at'].replace('Z','+00:00'))
                if moment.tzinfo is None:raise APIError('malformed_response','post_date_invalid')
                refs=post.get('referenced_posts',post.get('referenced_tweets',[]))
                if not isinstance(refs,list) or not all(isinstance(r,dict) for r in refs):raise APIError('malformed_response','post_references_invalid')
                normalized.append({'id':post['id'],'text':text,'created_at':post['created_at'],'author_id':owner['id'],
                                   'author':owner['username'],'is_repost':any(r.get('type')=='retweeted' for r in refs),
                                   'is_reply':any(r.get('type')=='replied_to' for r in refs),'is_promoted':False,
                                   'restricted':bool(post.get('withheld'))})
            return {'account':owner,'posts':normalized,'cursor':cursor}
        except APIError as exc:
            return {'error':str(exc),**({'diagnostic':exc.diagnostic} if exc.diagnostic else {}),
                    **({'problem_types':exc.problem_types} if exc.problem_types else {})}
        except (KeyError,ValueError,TypeError,AttributeError):
            return {'error':'malformed_response','diagnostic':stage+'_fields_invalid'}
