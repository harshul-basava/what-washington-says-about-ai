import importlib
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import httpx
import llm

ROOT=Path(__file__).resolve().parents[1]

class GatewayTests(unittest.TestCase):
    def test_invalid_actual_cost_never_corrupts_the_ledger(self):
        for cost in (float('nan'), float('inf'), -.01, 'invalid', True):
            with self.subTest(cost=cost), patch.object(llm, '_check'), \
                 patch.dict(llm.os.environ, {'OPENROUTER_API_KEY': 'test'}), \
                 patch.object(llm.httpx, 'post', return_value=httpx.Response(200,
                     content=__import__('json').dumps({'usage': {'cost': cost}}).encode())), \
                 patch.object(llm, '_log') as log:
                with self.assertRaises(ValueError):
                    llm.chat([], tag='test', retry_attempts=1)
                log.assert_not_called()

    def test_local_credit_check_identifies_a_request_that_never_started(self):
        with patch.object(llm, 'spent', return_value=500), patch.object(llm, 'BUDGETS', {'openrouter': 500}), \
             patch.object(llm.httpx, 'post') as post:
            with self.assertRaises(llm.BudgetExceeded) as caught:
                llm.chat([], tag='test', retry_attempts=1)
            self.assertTrue(getattr(caught.exception, 'rejected_before_inference', False))
            post.assert_not_called()

    def test_preflight_credit_rejection_retains_safe_metadata(self):
        payload={'error':{'code':402,'message':'Wait for pending requests.',
            'metadata':{'limit_source':'openrouter_in_flight_budget','reason':'in_flight_budget_exhausted'}}}
        response=httpx.Response(402,json=payload,headers={'Retry-After':'2'})
        with patch.object(llm,'_check'),patch.dict(llm.os.environ,{'OPENROUTER_API_KEY':'test'}),patch.object(llm.httpx,'post',return_value=response):
            with self.assertRaises(llm.OpenRouterRequestError) as caught:
                llm.chat([],tag='test',retry_attempts=1)
        self.assertTrue(caught.exception.rejected_before_inference)
        self.assertEqual(caught.exception.limit_source,'openrouter_in_flight_budget')
        self.assertEqual(caught.exception.retry_after,2)

    def test_bounded_call_can_disable_hidden_retries(self):
        with patch.object(llm,'_check'),patch.object(llm.time,'sleep'),patch.dict(llm.os.environ,{'OPENROUTER_API_KEY':'test'}), \
             patch.object(llm.httpx,'post',side_effect=httpx.ReadTimeout('timeout')) as post:
            with self.assertRaises(httpx.ReadTimeout):llm.chat([],tag='test',retry_attempts=1)
            self.assertEqual(post.call_count,1)

class ModelTests(unittest.TestCase):
    def test_build_can_be_deferred_for_complete_analysis_without_network(self):
        import federal_analysis as a
        from test_federal_analysis import FederalAnalysisTests
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);fixture=FederalAnalysisTests();fixture.a=a;fixture.fixture(root)
            with patch.object(a,'plan',return_value={'status':'ok'}),patch.object(a,'build',side_effect=AssertionError('Deferred build')),patch.object(llm.httpx,'get',side_effect=AssertionError('No repeated model lookup')):
                result=self.m.run(root,build_output=False,review_workers=2)
            self.assertEqual(result['requests'],0)

    @classmethod
    def setUpClass(cls):
        assert (ROOT/'federal_analysis_models.py').exists(),'Federal model runner is missing'
        cls.m=importlib.import_module('federal_analysis_models')

    def gateway(self,cost=0.01):
        rows=[]
        gateway=SimpleNamespace(BUDGETS={'openrouter':1,'monthly':{'openrouter':0.5}},BudgetExceeded=llm.BudgetExceeded,
            OpenRouterRequestError=getattr(llm,'OpenRouterRequestError',RuntimeError),
            spent=lambda _:sum(r[1] for r in rows),spent_this_month=lambda _:sum(r[1] for r in rows),
            _log=lambda provider,amount,tag,meta:rows.append((provider,amount,tag,meta)))
        def chat(messages,**kwargs):
            rows.append(('openrouter',cost or 0,kwargs['tag'],{}))
            return {'usage':{'cost':cost},'choices':[{'message':{'content':'{}'}}]}
        gateway.chat=chat
        return gateway,rows

    def test_persistent_reservation_releases_only_with_known_cost(self):
        gateway,rows=self.gateway();budget=self.m.Budget(0.5,False,{'model':{'pricing':{'prompt':'0.00001','completion':'0.00001'}}},gateway)
        budget.call('model',[{'role':'user','content':'hello'}],10,'test')
        self.assertAlmostEqual(gateway.spent('openrouter'),0.01)
        self.assertEqual(rows[0][3]['phase'],'reservation');self.assertEqual(rows[-1][3]['phase'],'reconciliation')
        gateway,rows=self.gateway(None);budget=self.m.Budget(0.5,False,{'model':{'pricing':{'prompt':'0.00001','completion':'0.00001'}}},gateway)
        budget.call('model',[{'role':'user','content':'hello'}],10,'test')
        self.assertGreater(gateway.spent('openrouter'),0)
        self.assertEqual(budget.uncertain,1)

    def test_budget_blocks_before_request(self):
        gateway,rows=self.gateway();budget=self.m.Budget(0.001,False,{'model':{'pricing':{'prompt':'1','completion':'1'}}},gateway)
        with self.assertRaises(llm.BudgetExceeded):budget.call('model',[{'role':'user','content':'hello'}],10,'test')
        self.assertEqual(rows,[])

    def test_only_confirmed_preflight_rejections_release_the_reservation(self):
        for source,release in [('openrouter_in_flight_budget',True),('openrouter_credits',True),(None,False)]:
            gateway,rows=self.gateway()
            def reject(*args,**kwargs):
                raise llm.OpenRouterRequestError(402,{'message':'Rejected.','metadata':{'limit_source':source}})
            gateway.chat=reject
            budget=self.m.Budget(0.5,False,{'model':{'pricing':{'prompt':'0.00001','completion':'0.00001'}}},gateway)
            with self.assertRaises(llm.OpenRouterRequestError):budget.call('model',[{'content':'hello'}],10,'test')
            self.assertEqual(gateway.spent('openrouter')==0,release)
            self.assertEqual(budget.uncertain,0 if release else 1)

    def test_daily_reservation_uses_only_reachable_price_tiers(self):
        pricing={'prompt':'0.00001','completion':'0.00005','overrides':[
            {'min_prompt_tokens':272000,'prompt':'0.00002','completion':'0.000075'}]}
        gateway,rows=self.gateway();gateway.BUDGETS={'openrouter':350,'monthly':{'openrouter':35}}
        budget=self.m.Budget(2,True,{'model':{'pricing':pricing}},gateway)
        budget.call('model',[{'role':'user','content':'x'*129000}],12000,'daily_test')
        self.assertAlmostEqual(rows[0][1],1.895)
        # Once the conservative input bound can enter the premium tier, reserve that rate.
        gateway,rows=self.gateway();gateway.BUDGETS={'openrouter':350}
        budget=self.m.Budget(10,False,{'model':{'pricing':pricing}},gateway)
        budget.call('model',[{'role':'user','content':'x'*272000}],12000,'test')
        self.assertAlmostEqual(rows[0][1],6.35)
        # An override without a known threshold remains possible and must be covered.
        pricing['overrides'][0].pop('min_prompt_tokens')
        gateway,rows=self.gateway();gateway.BUDGETS={'openrouter':350}
        budget=self.m.Budget(2,False,{'model':{'pricing':pricing}},gateway)
        with self.assertRaises(llm.BudgetExceeded):
            budget.call('model',[{'role':'user','content':'x'*129000}],12000,'test')
        self.assertEqual(rows,[])

    def test_zero_allowance_keeps_pending_work_without_network(self):
        from test_federal_analysis import FederalAnalysisTests
        import federal_analysis as a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fixture=FederalAnalysisTests();fixture.a=a;person,_=fixture.fixture(root)
            s={'sid':'s1','date':'2026-01-01','text':'We support strong AI oversight.','url':'https://example.gov/ai',
               'source_type':'web','verified':True,'attribution':{'kind':'personal','speaker':person['name']}}
            a.write(root/'evidence/executive_a.json',{'statements':[s]})
            with patch.object(llm.httpx,'get',side_effect=AssertionError('No network at zero allowance')):
                result=self.m.run(root,max_cost=0,workers=20)
            self.assertEqual(result['status'],'partial');self.assertEqual(result['pending_labels'],1)
            self.assertEqual(result['estimated_cost_usd'],0)
            observations=a.read(root/f'data/federal_analysis_snapshots/{a.today()}.json',{})
            self.assertIn('commerce',observations)
            self.assertNotIn('executive_a',observations)

    def test_complete_backfill_resumes_without_any_network(self):
        from test_federal_analysis import FederalAnalysisTests
        import federal_analysis as a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fixture=FederalAnalysisTests();fixture.a=a;person,_=fixture.fixture(root)
            ss=[{'sid':f's{i}','date':'2026-01-01','text':'We support specific rules for AI companies.','url':'https://example.gov/ai',
                 'source_type':'web','verified':True,'attribution':{'kind':'personal','speaker':person['name']}} for i in range(1,4)]
            a.write(root/'evidence/executive_a.json',{'statements':ss})
            settings=a.configuration(root)['settings'];models=settings['models']
            metadata={'data':[{'id':m,'pricing':{'prompt':'0','completion':'0'},'supported_parameters':[]} for m in models.values()]}
            response=SimpleNamespace(raise_for_status=lambda:None,json=lambda:metadata)
            attempt_tokens=[]
            def call(_budget,model,messages,max_tokens,tag,**options):
                import json
                stage=tag.removeprefix('federal_analysis_')
                if stage=='ds_0':
                    attempt_tokens.append(max_tokens)
                    if len(attempt_tokens)==1:return {'choices':[{'message':{'content':None}}]}
                if stage.startswith('ds_') or stage in ('sol','astra'):
                    value={'statements':{s['sid']:fixture.assessment({'regulation':2}) for s in ss}}
                elif stage.startswith('reg_'):value={'stances':{k:{'stance':0,'sids':[],'why':'No stance.'} for k in a.AREA_IDS}}
                else:value={'sentences':[{'text':'Supports rules for AI companies.','sids':['s1']}]}
                return {'id':'test-generation','choices':[{'message':{'content':json.dumps(value)}}]}
            with patch.object(llm.httpx,'get',return_value=response),patch.object(self.m.Budget,'call',call):
                result=self.m.run(root,max_cost=1,workers=1)
            self.assertEqual(result['status'],'ok');self.assertEqual(result['pending_labels'],0)
            self.assertEqual(attempt_tokens,[settings['max_output_tokens'],2*settings['max_output_tokens']])
            exported=a.read(root/'site/data/federal_analysis.json')
            member=next(m for m in exported['members'] if m['id']=='executive_a')
            self.assertEqual(member['scores']['regulation'],2);self.assertEqual(member['summary']['sids'],['s1'])
            with patch.object(llm.httpx,'get',side_effect=AssertionError('Resumed complete analysis needs no network')):
                again=self.m.run(root,max_cost=1)
            self.assertEqual(again['requests'],0)
            ss[0]['text']='We oppose binding rules for AI companies.'
            a.write(root/'evidence/executive_a.json',{'statements':ss})
            backlog=a.plan(root)
            self.assertEqual(backlog['pending_labels'],1)
            self.assertEqual(backlog['pending_regulation'],1)
            self.assertEqual(backlog['pending_summaries'],1)

class DailySchedulerTests(unittest.TestCase):
    def setUp(self):
        import federal_analysis as a
        import federal_analysis_models as m
        from test_federal_analysis import FederalAnalysisTests
        self.a=a;self.m=m;self.fixture=FederalAnalysisTests();self.fixture.a=a

    def statements(self,name,count=3):
        return [{'sid':f's{i}','date':'2026-01-01','text':f'{name} supports AI oversight. Excerpt {i}.',
                 'url':'https://example.gov/ai','source_type':'web','verified':True,
                 'attribution':{'kind':'personal','speaker':name}} for i in range(1,count+1)]

    def run_fake(self,root,allowance=1,daily=True,ids=None,stages=None,invalid=False,workers=1,pricing=None):
        import contextlib
        import io
        import json
        a=self.a;rows=[];calls=[]
        settings=a.configuration(root)['settings']
        metadata={'data':[{'id':m,'pricing':pricing or {'prompt':'0','completion':'0','request':'1'},
                          'supported_parameters':[]} for m in settings['models'].values()]}
        response=SimpleNamespace(raise_for_status=lambda:None,json=lambda:metadata)
        def chat(messages,**kwargs):
            stage=kwargs['tag'].removeprefix('daily_').removeprefix('federal_analysis_')
            context=json.JSONDecoder().raw_decode(messages[0]['content'].split('Subject and role context:\n')[1])[0]
            pid=context['id']
            ss=json.JSONDecoder().raw_decode(messages[1]['content'].split('Evidence:\n')[1])[0]
            labels,profiles=a.state(root)
            if stage in ('sol','astra'):
                for s in ss:
                    self.assertEqual(a.resolve_labels(labels['profiles'][pid][s['sid']],settings).get('next'),stage)
            if stage=='reg_astra':
                resolved=a.resolve_regulation(profiles['profiles'][pid])
                self.assertEqual(resolved['status'],'pending');self.assertTrue(resolved.get('disputed'))
            calls.append((stage,pid));rows.append(1)
            if invalid is True or (callable(invalid) and invalid(stage,pid,{s['sid'] for s in ss})):value={}
            elif stage.startswith('ds_') or stage in ('sol','astra'):
                value={'statements':{s['sid']:self.fixture.assessment({'x_risk':0 if stage=='sol' else 2 if stage=='astra' else 3}) for s in ss}}
            elif stage.startswith('reg_'):
                value={'stances':{k:{'stance':0,'sids':[],'why':'No stance.'} for k in a.AREA_IDS}}
                value['stances'][a.AREA_IDS[0]]={'stance':-2 if stage=='reg_sol' else 2,'sids':[ss[0]['sid']],'why':'Supports oversight.'}
                if stage=='reg_astra':value['stances']={a.AREA_IDS[0]:value['stances'][a.AREA_IDS[0]]}
            else:value={'sentences':[{'text':'Supports AI oversight.','sids':[ss[0]['sid']]}]}
            return {'id':'test-generation','usage':{'cost':1},'choices':[{'message':{'content':json.dumps(value)}}]}
        with patch.dict(llm.os.environ,{'OPENROUTER_API_KEY':'test'}), \
             patch.object(llm,'BUDGETS',{'openrouter':10000,'monthly':{'openrouter':10000}}), \
             patch.object(llm,'spent',side_effect=lambda _:sum(rows)), \
             patch.object(llm,'spent_this_month',side_effect=lambda _:sum(rows)), \
             patch.object(llm,'_log',side_effect=lambda provider,cost,tag,meta:rows.append(cost)), \
             patch.object(llm,'chat',side_effect=chat),patch.object(llm.httpx,'get',return_value=response), \
             contextlib.redirect_stdout(io.StringIO()):
            result=self.m.run(root,max_cost=allowance+0.01,workers=workers,daily=daily,ids=ids,stages=stages)
        self.assertLessEqual(result['estimated_cost_usd'],allowance)
        self.assertFalse(any(e['error']=='AssertionError' for e in result['errors']),result['errors'])
        return result,calls

    def test_daily_small_caps_finish_old_reviews_and_new_agency_despite_new_evidence(self):
        import copy
        a=self.a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);person,_=self.fixture.fixture(root)
            registry=a.read(root/'config/policy_subjects.json')
            older=copy.deepcopy(person);older.update(id='executive_b',name='Official B')
            registry['subjects'].append(older);a.write(root/'config/policy_subjects.json',registry)
            old_ss=self.statements(older['name']);a.write(root/'evidence/executive_b.json',{'statements':old_ss})
            config=a.configuration(root)
            old_labels={}
            for s in old_ss:
                entry=self.fixture.entry({'x_risk':3})
                for result in entry['assessments'].values():result['model']=config['settings']['models']['deepseek']
                old_labels[s['sid']]={**entry,'input_hash':a.fingerprint(older,[s],'labels',config)}
            a.write(root/a.LABEL_PATH,{'profiles':{'executive_b':old_labels}})
            all_calls=[]
            for day in range(40):
                # Fresh first-profile work must not monopolize each invocation.
                a.write(root/'evidence/executive_a.json',{'statements':self.statements(person['name'],day+1)})
                if day==3:
                    agency_ss=self.statements('Commerce')
                    for s in agency_ss:s['attribution'].update(kind='institutional',organization_id='commerce')
                    a.write(root/'evidence/commerce.json',{'statements':agency_ss})
                result,calls=self.run_fake(root);all_calls.extend(calls)
                if day==0:
                    self.assertGreater(result['pending_labels'],0)
                    self.assertGreater(result['pending_regulation'],0)
                    detail=a.read(root/'site/data/federal_analysis/executive_a.json')['profile']
                    self.assertTrue(all(value is None for value in detail['scores'].values()))
            for pid in ('executive_b','commerce'):
                detail=a.read(root/f'site/data/federal_analysis/{pid}.json')['profile']
                self.assertEqual(detail['summary']['status'],'complete',pid)
                self.assertEqual(detail['regulation']['status'],'complete',pid)
                self.assertEqual(detail['scores']['x_risk'],2.5,pid)
            self.assertTrue((root/'data/federal_analysis_scheduler.json').exists())
            self.assertIn(('astra','executive_b'),all_calls)
            self.assertIn(('reg_astra','commerce'),all_calls)
            self.assertGreater(result['pending_labels'],0)

    def test_manual_scoped_run_keeps_order_and_does_not_change_daily_cursor(self):
        a=self.a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);person,_=self.fixture.fixture(root)
            a.write(root/'evidence/executive_a.json',{'statements':self.statements(person['name'])})
            cursor=root/'data/federal_analysis_scheduler.json'
            a.write(cursor,{'version':1,'next_stage':'summary','last_profile':{'ds_0':'executive_a'}})
            before=cursor.read_bytes()
            result,calls=self.run_fake(root,allowance=20,daily=False,ids=['executive_a'])
            self.assertEqual(result['status'],'ok')
            self.assertEqual([stage for stage,pid in calls],['ds_0','ds_1','ds_2','sol','astra','reg_ds','reg_sol','reg_astra','summary'])
            self.assertEqual(cursor.read_bytes(),before)

    def test_daily_invalid_responses_remain_pending_without_silence_scores(self):
        a=self.a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);person,_=self.fixture.fixture(root)
            a.write(root/'evidence/executive_a.json',{'statements':self.statements(person['name'])})
            result,_=self.run_fake(root,allowance=20,invalid=True)
            self.assertEqual(result['status'],'partial')
            self.assertEqual(result['pending_labels'],3)
            self.assertEqual(result['pending_regulation'],1)
            self.assertEqual(result['pending_summaries'],1)
            detail=a.read(root/'site/data/federal_analysis/executive_a.json')['profile']
            self.assertTrue(all(value is None for value in detail['scores'].values()))
            self.assertEqual(detail['regulation']['status'],'pending')
            self.assertEqual(detail['summary']['status'],'pending')

    def test_daily_retry_gives_a_budget_blocked_stage_a_full_allowance(self):
        a=self.a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);person,_=self.fixture.fixture(root);calls=[]
            for day in range(4):
                a.write(root/'evidence/executive_a.json',{'statements':self.statements(person['name'],day+1)})
                _,done=self.run_fake(root,stages=['ds_0','summary']);calls.extend(done)
            self.assertIn(('summary','executive_a'),calls)

    def test_daily_oversized_profile_does_not_block_cheaper_profile_in_same_stage(self):
        a=self.a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);person,_=self.fixture.fixture(root)
            large=self.statements(person['name'],1);large[0]['text']='AI oversight. '*10000
            a.write(root/'evidence/executive_a.json',{'statements':large})
            agency=self.statements('Commerce',1)
            agency[0]['attribution'].update(kind='institutional',organization_id='commerce')
            a.write(root/'evidence/commerce.json',{'statements':agency})
            a.write(root/'data/federal_analysis_scheduler.json',{
                'version':1,'next_stage':'ds_0','last_profile':{'ds_0':'commerce'}})
            pricing={'prompt':'0.00001','completion':'0'}
            for _ in range(3):result,_=self.run_fake(root,stages=['ds_0'],pricing=pricing)
            labels,_=a.state(root)
            self.assertIn('ds_0',labels.get('profiles',{}).get('commerce',{}).get('s1',{}).get('assessments',{}))
            self.assertEqual(labels['profiles']['executive_a']['s1']['assessments'],{})
            self.assertGreater(result['pending_labels'],0)

    def test_daily_profile_turn_survives_competing_workers(self):
        import threading
        a=self.a
        original=self.m.Budget.call
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);person,_=self.fixture.fixture(root);calls=[]
            for day in range(3):
                a.write(root/'evidence/executive_a.json',{'statements':self.statements(person['name'],day+1)})
                agency=self.statements('Commerce',day+1)
                for s in agency:s['attribution'].update(kind='institutional',organization_id='commerce')
                a.write(root/'evidence/commerce.json',{'statements':agency})
                competitor_finished=threading.Event()
                def delayed(budget,model,messages,*args,**kwargs):
                    # An older profile can reach the reservation after its competitor.
                    slower='"id": "executive_a"' in messages[0]['content']
                    if slower:competitor_finished.wait(0.2)
                    try:return original(budget,model,messages,*args,**kwargs)
                    finally:
                        if not slower:competitor_finished.set()
                with patch.object(self.m.Budget,'call',delayed):
                    _,done=self.run_fake(root,stages=['ds_0'],workers=4);calls.extend(done)
            self.assertIn(('ds_0','executive_a'),calls)

    def test_daily_invalid_profile_does_not_consume_every_retry_allowance(self):
        a=self.a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);person,_=self.fixture.fixture(root)
            a.write(root/'evidence/executive_a.json',{'statements':self.statements(person['name'],1)})
            agency=self.statements('Commerce',1)
            agency[0]['attribution'].update(kind='institutional',organization_id='commerce')
            a.write(root/'evidence/commerce.json',{'statements':agency})
            for _ in range(3):
                result,_=self.run_fake(root,stages=['ds_0'],invalid=lambda stage,pid,sids:pid=='commerce')
            labels,_=a.state(root)
            self.assertIn('ds_0',labels.get('profiles',{}).get('executive_a',{}).get('s1',{}).get('assessments',{}))
            self.assertEqual(labels['profiles']['commerce']['s1']['assessments'],{})
            self.assertGreater(result['pending_labels'],0)

    def test_daily_invalid_retry_does_not_block_a_later_stage(self):
        a=self.a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);person,_=self.fixture.fixture(root)
            a.write(root/'evidence/executive_a.json',{'statements':self.statements(person['name'],1)})
            for _ in range(4):
                result,_=self.run_fake(root,stages=['ds_0','summary'],invalid=lambda stage,pid,sids:stage=='ds_0')
            profile=a.read(root/'site/data/federal_analysis/executive_a.json')['profile']
            self.assertEqual(profile['summary']['status'],'complete')
            self.assertEqual(result['pending_labels'],1)

    def test_daily_oversized_batch_does_not_block_smaller_batch_for_same_profile(self):
        a=self.a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);person,_=self.fixture.fixture(root)
            settings_path=root/'config/federal_analysis.json'
            settings=a.read(settings_path);settings['labels_batch_size']=2;a.write(settings_path,settings)
            statements=self.statements(person['name']);statements[0]['text']='AI oversight. '*10000
            a.write(root/'evidence/executive_a.json',{'statements':statements})
            pricing={'prompt':'0.00001','completion':'0'}
            for _ in range(4):
                result,_=self.run_fake(root,stages=['ds_0'],pricing=pricing)
            labels,_=a.state(root)
            entries=labels.get('profiles',{}).get('executive_a',{})
            self.assertIn('ds_0',entries.get('s3',{}).get('assessments',{}))
            self.assertEqual(entries['s1']['assessments'],{})
            self.assertEqual(entries['s2']['assessments'],{})
            self.assertEqual(result['pending_labels'],3)

    def test_daily_invalid_first_batch_does_not_block_later_batches(self):
        a=self.a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);person,_=self.fixture.fixture(root)
            settings_path=root/'config/federal_analysis.json'
            settings=a.read(settings_path);settings['labels_batch_size']=1;a.write(settings_path,settings)
            rejected=[]
            def invalid(stage,pid,sids):
                if 's1' in sids:rejected.append('s1');return True
                return False
            for day in range(6):
                a.write(root/'evidence/executive_a.json',{'statements':self.statements(person['name'],day+2)})
                self.run_fake(root,stages=['ds_0'],invalid=invalid)
            labels,_=a.state(root)
            entries=labels.get('profiles',{}).get('executive_a',{})
            self.assertIn('ds_0',entries.get('s2',{}).get('assessments',{}))
            self.assertNotIn('ds_0',entries['s1']['assessments'])
            self.assertGreaterEqual(len(rejected),2)
