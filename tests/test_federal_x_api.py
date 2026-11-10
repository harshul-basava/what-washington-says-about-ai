import copy
import importlib
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
import llm

USER={'id':'7','username':'OfficialA','name':'Official A','protected':False}
TEXT='We support strong AI export controls to protect national security and prevent harmful military uses.'
POST={'id':'100','author_id':'7','text':'Shortened text','note_tweet':{'text':TEXT},
      'created_at':'2026-11-01T12:00:00Z','referenced_tweets':[{'id':'200','type':'quoted'}]}
REQUEST={'handle':'OfficialA','query':'from:OfficialA (AI OR "artificial intelligence") -is:retweet',
         'start_time':'2023-01-01T00:00:00Z','end_time':'2026-11-02T00:00:00Z','cursor':None}
ANCHORED_REQUEST=REQUEST|{'ownership_anchor_post_id':'900'}


class OfficialAPITests(unittest.TestCase):
    def setUp(self):
        self.api=importlib.import_module('federal_x_api') if (ROOT/'scripts/federal_x_api.py').exists() else None
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.state={'accounts':{}}
        self.now=time.time();self.calls=[]
        for patcher in (patch.object(llm,'LEDGER',self.root/'data/cost_ledger.jsonl'),
                        patch.object(llm,'BUDGETS',{'x':150,'monthly':{'x':10}}),
                        patch.dict(os.environ,{'X_BEARER_TOKEN':'official-test-bearer'},clear=True)):
            patcher.start();self.addCleanup(patcher.stop)

    def client(self, handler=None, max_cost=3, checkpoint=None):
        self.assertIsNotNone(self.api,'The official federal API transport is missing')
        def send(request):
            self.calls.append(request)
            if handler:return handler(request)
            if '/users/' in request.url.path:return httpx.Response(200,json={'data':USER})
            return httpx.Response(200,json={'data':[POST],'meta':{'result_count':1,'next_token':'next'}})
        http=httpx.Client(transport=httpx.MockTransport(send));self.addCleanup(http.close)
        for patcher in (patch.object(self.api.time,'time',side_effect=lambda:self.now),
                        patch.object(self.api.time,'sleep',side_effect=self.advance)):
            patcher.start();self.addCleanup(patcher.stop)
        return self.api.Client(self.root,self.state,max_cost=max_cost,daily=True,get=http.get,checkpoint=checkpoint)

    def advance(self,seconds):self.now+=seconds

    def records(self):
        return [json.loads(s) for s in llm.LEDGER.read_text().splitlines()] if llm.LEDGER.exists() else []

    def test_full_archive_request_retains_original_author_text_and_cursor(self):
        client=self.client();result=client(REQUEST)
        self.assertEqual(result['posts'][0]['text'],TEXT)
        self.assertEqual(result['posts'][0]['author_id'],'7')
        self.assertFalse(result['posts'][0]['is_repost'])
        self.assertEqual(result['cursor'],'next')
        req=self.calls[-1]
        self.assertEqual(req.url.host,'api.x.com')
        self.assertEqual(req.url.path,'/2/tweets/search/all')
        self.assertEqual(req.url.params['max_results'],'100')
        self.assertEqual(req.url.params['start_time'],'2023-01-01T00:00:00Z')
        self.assertEqual(req.url.params['end_time'],'2026-11-02T00:00:00Z')
        self.assertNotIn('expansions',req.url.params)
        self.assertEqual(req.headers['authorization'],'Bearer official-test-bearer')
        self.assertAlmostEqual(sum(r['cost'] for r in self.records()),0.015)
        self.assertNotIn('official-test-bearer',json.dumps(result)+json.dumps(self.records()))
        self.assertEqual([r.url.path for r in self.calls],['/2/users/by/username/OfficialA','/2/tweets/search/all'])

    def anchor_response(self, req, **changes):
        if '/users/' in req.url.path:return httpx.Response(200,json={'data':USER})
        if req.url.path=='/2/tweets/search/all':
            return httpx.Response(200,json={'data':[POST],'meta':{'result_count':1}})
        return httpx.Response(200,json={'data':{'id':req.url.path.rsplit('/',1)[-1],'author_id':'7'}|changes})

    def test_matching_ownership_anchor_is_checked_before_archive_search(self):
        result=self.client(self.anchor_response)(ANCHORED_REQUEST)
        self.assertEqual([req.url.path for req in self.calls],
            ['/2/users/by/username/OfficialA','/2/tweets/900','/2/tweets/search/all'])
        self.assertIn('author_id',self.calls[1].url.params['tweet.fields'])
        self.assertEqual([p['id'] for p in result['posts']],['100'])
        self.assertAlmostEqual(sum(r['cost'] for r in self.records()),0.020)

    def test_ownership_anchor_mismatch_cannot_search_or_replace_a_pin(self):
        pin={'handle':'OfficialA','user_id':'7'}
        self.state['accounts']['official_a']=pin.copy()
        result=self.client(lambda req:self.anchor_response(req,author_id='8'))(ANCHORED_REQUEST)
        self.assertEqual(result,{'error':'account_identity_changed','diagnostic':'ownership_anchor_author_mismatch'})
        self.assertEqual([r.url.path for r in self.calls],['/2/users/by/username/OfficialA','/2/tweets/900'])
        self.assertEqual(self.state['accounts']['official_a'],pin)
        self.assertNotIn('ownership_anchors',self.state)

    def test_unavailable_ownership_anchor_leaves_collection_pending(self):
        for status,payload in [(404,{'detail':'private-provider-body'}),(200,{})]:
            with self.subTest(status=status):
                self.calls.clear()
                def send(req):
                    if req.url.path=='/2/tweets/900':return httpx.Response(status,json=payload)
                    return self.anchor_response(req)
                result=self.client(send)(ANCHORED_REQUEST)
                self.assertEqual(result,{'error':'ownership_anchor_unavailable'})
                self.assertEqual([r.url.path for r in self.calls],['/2/users/by/username/OfficialA','/2/tweets/900'])
                self.assertNotIn('ownership_anchors',self.state)

    def test_ownership_anchor_response_must_identify_the_requested_post(self):
        result=self.client(lambda req:self.anchor_response(req,id='901'))(ANCHORED_REQUEST)
        self.assertEqual(result,{'error':'malformed_response','diagnostic':'ownership_anchor_identity_invalid'})
        self.assertEqual(len(self.calls),2)

    def test_ownership_anchor_cache_survives_restart_and_rechecks_changed_post(self):
        saved=[]
        first=self.client(self.anchor_response,checkpoint=lambda:saved.append(copy.deepcopy(self.state)))
        self.assertEqual(first(ANCHORED_REQUEST)['posts'][0]['id'],'100')
        self.state=saved[-1]
        second=self.client(self.anchor_response)
        self.assertEqual(second(ANCHORED_REQUEST)['posts'][0]['id'],'100')
        self.assertEqual(second(ANCHORED_REQUEST|{'ownership_anchor_post_id':'901'})['posts'][0]['id'],'100')
        self.assertEqual([req.url.path for req in self.calls],['/2/users/by/username/OfficialA',
            '/2/tweets/900','/2/tweets/search/all','/2/users/by/username/OfficialA',
            '/2/tweets/search/all','/2/tweets/901','/2/tweets/search/all'])

    def test_ownership_anchor_and_search_reservation_fit_before_contact(self):
        result=self.client(self.anchor_response,max_cost=0.064)(ANCHORED_REQUEST)
        self.assertEqual(result,{'error':'budget_exceeded'})
        self.assertEqual(self.calls,[])

    def test_invalid_ownership_anchor_is_rejected_without_a_request(self):
        for bad in (None,900,'','0','/900','９００'):
            with self.subTest(anchor=bad):
                result=self.client()(REQUEST|{'ownership_anchor_post_id':bad})
                self.assertEqual(result,{'error':'malformed_response','diagnostic':'ownership_anchor_id_invalid'})
        self.assertEqual(self.calls,[])

    def test_resume_reuses_verified_lookup_and_forwards_next_token(self):
        client=self.client();client(REQUEST);client(REQUEST|{'cursor':'opaque-next'})
        self.assertEqual(len(self.calls),3)
        self.assertEqual(self.calls[-1].url.params['next_token'],'opaque-next')
        self.assertEqual(self.calls[-1].url.params['end_time'],'2026-11-02T00:00:00Z')
        self.assertAlmostEqual(client.spent,0.020)

    def test_current_post_field_names_keep_full_text_and_repost_flag(self):
        post=copy.deepcopy(POST);post['note_post']=post.pop('note_tweet')
        post['referenced_posts']=[{'id':'200','type':'retweeted'}];post.pop('referenced_tweets')
        def send(req):
            return httpx.Response(200,json={'data':USER} if '/users/' in req.url.path else
                                  {'data':[post],'meta':{'result_count':1}})
        result=self.client(send)(REQUEST)
        self.assertEqual(result['posts'][0]['text'],TEXT)
        self.assertTrue(result['posts'][0]['is_repost'])

    def test_empty_page_with_cursor_keeps_pagination(self):
        def send(req):
            return httpx.Response(200,json={'data':USER} if '/users/' in req.url.path else
                                  {'meta':{'result_count':0,'next_token':'continue'}})
        result=self.client(send)(REQUEST)
        self.assertEqual(result['posts'],[])
        self.assertEqual(result['cursor'],'continue')

    def test_partial_error_is_charged_but_cannot_complete_a_search(self):
        def send(req):
            return httpx.Response(200,json={'data':USER} if '/users/' in req.url.path else
                                  {'data':[POST],'meta':{'result_count':1},'errors':[{'detail':'secret-provider-body'}]})
        result=self.client(send)(REQUEST)
        self.assertEqual(result,{'error':'malformed_response','diagnostic':'search_response_errors'})
        self.assertAlmostEqual(sum(r['cost'] for r in self.records()),0.015)

    def test_partial_error_exposes_only_allowlisted_problem_types(self):
        def send(req):
            return httpx.Response(200,json={'data':USER} if '/users/' in req.url.path else
                {'data':[POST],'meta':{'result_count':1},'errors':[
                    {'type':'https://api.x.com/2/problems/resource-not-found','detail':'private details'},
                    {'type':'https://api.twitter.com/2/problems/internal-error','value':'private value'},
                    {'type':'https://untrusted.example/secret','detail':'official-test-bearer'}]})
        result=self.client(send)(REQUEST)
        self.assertEqual(result,{'error':'malformed_response','diagnostic':'search_response_errors',
                                 'problem_types':['internal-error','resource-not-found']})
        self.assertNotIn('private',json.dumps(result))
        self.assertNotIn('official-test-bearer',json.dumps(result))

    def test_author_failure_has_a_safe_diagnostic_and_keeps_response_private(self):
        def send(req):
            return httpx.Response(200,json={'data':USER} if '/users/' in req.url.path else
                                  {'data':[POST|{'author_id':'8','text':'private response text'}],
                                   'meta':{'result_count':1}})
        result=self.client(send)(REQUEST)
        self.assertEqual(result,{'error':'malformed_response','diagnostic':'post_identity_invalid'})

    def test_missing_account_errors_have_a_safe_lookup_diagnostic(self):
        result=self.client(lambda req:httpx.Response(200,json={
            'errors':[{'detail':'private lookup details','value':'private value'}]}))(REQUEST)
        self.assertEqual(result,{'error':'malformed_response','diagnostic':'lookup_response_errors'})
        self.assertEqual(len(self.calls),1)
        self.assertAlmostEqual(sum(r['cost'] for r in self.records()),0)

    def test_changed_numeric_identity_is_rejected_before_search(self):
        self.state['accounts']['official_a']={'handle':'OfficialA','user_id':'8'}
        result=self.client()(REQUEST)
        self.assertEqual(result,{'error':'account_identity_changed'})
        self.assertEqual(len(self.calls),1)

    def test_protected_account_is_rejected_before_search(self):
        result=self.client(lambda req:httpx.Response(200,json={'data':USER|{'protected':True}}))(REQUEST)
        self.assertEqual(result,{'error':'account_unavailable'})
        self.assertEqual(len(self.calls),1)

    def test_budget_reserves_lookup_and_minimum_page_before_contact(self):
        result=self.client(max_cost=0.059)(REQUEST)
        self.assertEqual(result,{'error':'budget_exceeded'})
        self.assertEqual(self.calls,[])

    def test_page_size_shrinks_to_remaining_monthly_budget(self):
        llm._log('x',9.94,'daily_previous',{})
        result=self.client()(REQUEST)
        self.assertNotIn('error',result)
        self.assertEqual(self.calls[-1].url.params['max_results'],'10')
        self.assertLessEqual(llm.spent_this_month('x'),10)

    def test_lifetime_budget_stops_before_a_lookup(self):
        llm._log('x',149.95,'previous',{})
        self.assertEqual(self.client()(REQUEST),{'error':'budget_exceeded'})
        self.assertEqual(self.calls,[])

    def test_rate_limit_cooldown_survives_another_client(self):
        def send(req):
            if '/users/' in req.url.path:return httpx.Response(200,json={'data':USER})
            return httpx.Response(429,headers={'x-rate-limit-reset':str(int(self.now+1800))},json={'detail':'private-provider-error'})
        client=self.client(send);result=client(REQUEST)
        self.assertEqual(result,{'error':'rate_limited'})
        self.assertGreater(self.state['retry_after'],self.now+1700)
        count=len(self.calls)
        self.assertEqual(self.client()(REQUEST),{'error':'rate_limited'})
        self.assertEqual(len(self.calls),count)

    def test_pacing_is_saved_before_http_and_cooldown_before_return(self):
        saved=[]
        def save():saved.append(copy.deepcopy(self.state))
        def send(req):
            self.assertGreater(saved[-1]['api_next_request_at'],self.now)
            return httpx.Response(429,headers={'x-rate-limit-reset':str(int(self.now+1800))})
        result=self.client(send,checkpoint=save)(REQUEST)
        self.assertEqual(result,{'error':'rate_limited'})
        self.assertGreater(saved[-1]['retry_after'],self.now+1700)

    def test_unknown_timeout_cost_reserves_the_requested_resources(self):
        def send(req):
            if '/users/' in req.url.path:return httpx.Response(200,json={'data':USER})
            raise httpx.ReadTimeout('sensitive-provider-error')
        client=self.client(send,max_cost=0.06)
        self.assertEqual(client(REQUEST),{'error':'timeout'})
        self.assertAlmostEqual(client.spent,0.06)
        self.assertTrue(self.records()[-1]['cost_uncertain'])

    def test_process_interruption_keeps_cost_reserved_for_next_invocation(self):
        llm.BUDGETS['monthly']['x']=0.06
        def send(req):
            if '/users/' in req.url.path:return httpx.Response(200,json={'data':USER})
            self.assertAlmostEqual(llm.spent_this_month('x'),0.06)
            raise KeyboardInterrupt()
        client=self.client(send,max_cost=0.06)
        with self.assertRaises(KeyboardInterrupt):client(REQUEST)
        count=len(self.calls)
        self.assertAlmostEqual(llm.spent('x'),0.06)
        self.assertEqual(self.client()(REQUEST),{'error':'budget_exceeded'})
        self.assertEqual(len(self.calls),count)

    def test_authentication_and_credit_errors_are_sanitized(self):
        for status,error in [(401,'authentication_failed'),(403,'authentication_failed'),(402,'credits_exhausted')]:
            with self.subTest(status=status):
                result=self.client(lambda req:httpx.Response(status,json={'detail':'sensitive-token'}))(REQUEST)
                self.assertEqual(result,{'error':error})


if __name__=='__main__':unittest.main()
