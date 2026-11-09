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
                result=self.m.run(root,max_cost=0)
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
