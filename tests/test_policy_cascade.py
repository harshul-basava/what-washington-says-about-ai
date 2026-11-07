import copy
import json
import tempfile
import unittest
from pathlib import Path

import policy_judgments as p
import policy_cascade as c
from test_policy_judgments import ITEM, REGISTRY

STRATEGY = {'kind':'confidence_cascade', 'version':1, 'primary_model':'deepseek/test',
            'reviewer_model':'openai/test', 'threshold':0.8}


def label(stance='support', confidence=0.9):
    return {'stance':stance, 'reason':'The speaker endorses the bill.', 'facets':[],
            'confidence':confidence, 'confidence_reason':'The endorsement is explicit.'}


def save(saved, role, value, item=ITEM, registry=REGISTRY, strategy=STRATEGY):
    target=item['targets'][0]
    c.save_result(saved, item, target, role, value, registry, 'rubric', 'confidence', strategy, 'gen-test')


class CascadeTests(unittest.TestCase):
    def test_confidence_rejects_missing_nonfinite_boolean_and_out_of_range(self):
        for score in [None, True, '0.9', -0.1, 1.1, float('nan'), float('inf')]:
            with self.subTest(score=score):
                raw={'judgments':[{'key':ITEM['key'],'targets':{ITEM['targets'][0]:label(confidence=score)}}]}
                with self.assertRaises(ValueError):
                    c.validate_response(json.dumps(raw), [ITEM], REGISTRY)
        raw={'judgments':[{'key':ITEM['key'],'targets':{ITEM['targets'][0]:label(confidence=0)}}]}
        self.assertEqual(c.validate_response(json.dumps(raw),[ITEM],REGISTRY)[ITEM['key']][ITEM['targets'][0]]['confidence'],0)

    def test_boundary_accepts_primary_and_does_not_request_reviewer(self):
        saved={}
        save(saved,'deepseek',label(confidence=0.8))
        record=c.resolve(ITEM,ITEM['targets'][0],saved,REGISTRY,'rubric','confidence',STRATEGY)
        self.assertEqual(record['stance'],'support')
        self.assertEqual(record['final_judge'],'deepseek')
        self.assertEqual(c.jobs([ITEM],saved,REGISTRY,'rubric','confidence',STRATEGY,'astra',20),[])

    def test_uncertain_irrelevance_stays_pending_until_astra(self):
        saved={}
        save(saved,'deepseek',label('not_relevant',0.79))
        record=c.resolve(ITEM,ITEM['targets'][0],saved,REGISTRY,'rubric','confidence',STRATEGY)
        self.assertEqual(record['stance'],'pending')
        self.assertEqual(record['review_status'],'awaiting_astra')
        self.assertEqual(p.summarize([record],1)['coverage'],'pending')
        work=c.jobs([ITEM],saved,REGISTRY,'rubric','confidence',STRATEGY,'astra',20)
        self.assertEqual(work,[('astra',[ITEM])])

    def test_astra_resolves_disagreement_and_retains_both_assessments(self):
        saved={}
        save(saved,'deepseek',label('support',0.7))
        save(saved,'astra',label('oppose',0.93))
        r=c.resolve(ITEM,ITEM['targets'][0],saved,REGISTRY,'rubric','confidence',STRATEGY)
        self.assertEqual(r['stance'],'oppose')
        self.assertEqual(r['final_judge'],'astra')
        self.assertEqual(r['confidence'],0.93)
        self.assertTrue(r['model_disagreement'])
        self.assertEqual(set(r['judges']),{'deepseek','astra'})
        self.assertFalse(r['review_required'])

    def test_uncertain_astra_is_human_review_not_accepted_irrelevance(self):
        saved={}
        save(saved,'deepseek',label('not_relevant',0.6))
        save(saved,'astra',label('not_relevant',0.7))
        r=c.resolve(ITEM,ITEM['targets'][0],saved,REGISTRY,'rubric','confidence',STRATEGY)
        self.assertEqual(r['stance'],'review_required')
        self.assertTrue(r['review_required'])
        self.assertEqual(p.summarize([r],1)['coverage'],'pending')
        self.assertEqual(p.summarize([r],1)['human_review'],1)

    def test_cache_rejects_evidence_prompt_model_changes_but_threshold_can_reroute(self):
        saved={}
        save(saved,'deepseek',label(confidence=0.85))
        for item,rubric,confidence,strategy in [({**ITEM,'text':'Changed'},'rubric','confidence',STRATEGY),
            (ITEM,'new rubric','confidence',STRATEGY),(ITEM,'rubric','new confidence',STRATEGY),
            (ITEM,'rubric','confidence',{**STRATEGY,'primary_model':'other'})]:
            self.assertEqual(c.resolve(item,item['targets'][0],saved,REGISTRY,rubric,confidence,strategy)['stance'],'pending')
        high={**STRATEGY,'threshold':0.9}
        self.assertEqual(c.jobs([ITEM],saved,REGISTRY,'rubric','confidence',high,'deepseek',20),[])
        self.assertEqual(len(c.jobs([ITEM],saved,REGISTRY,'rubric','confidence',high,'astra',20)),1)

    def test_only_low_confidence_targets_go_to_astra(self):
        reg=copy.deepcopy(REGISTRY)
        reg['policies'].append({**reg['policies'][0],'id':'other'})
        item={**ITEM,'targets':[ITEM['targets'][0],'other']}
        saved={}
        save(saved,'deepseek',label(confidence=0.95),item,reg)
        c.save_result(saved,item,'other','deepseek',label(confidence=0.6),reg,'rubric','confidence',STRATEGY,'gen-test')
        work=c.jobs([item],saved,reg,'rubric','confidence',STRATEGY,'astra',20)
        self.assertEqual(work[0][1][0]['targets'],['other'])
        messages=c.messages(work[0][1],reg,'rubric','confidence','astra')
        self.assertNotIn('0.6',json.dumps(messages))
        self.assertNotIn('gen-test',json.dumps(messages))

    def test_chart_facets_come_from_final_judge_not_two_model_agreement(self):
        saved={}
        value=label(); value['facets']=['mandatory']
        reg=copy.deepcopy(REGISTRY); reg['policies'][0]['facets']=['mandatory']
        save(saved,'deepseek',value,registry=reg)
        r=c.resolve(ITEM,ITEM['targets'][0],saved,reg,'rubric','confidence',STRATEGY)
        r.update(sid='s1',date='2026-08-01')
        chart=p.chart_record('P',r)
        self.assertEqual(chart['facets_final'],['mandatory'])
        self.assertEqual(chart['final_judge'],'deepseek')

    def test_bad_threshold_fails_without_calls(self):
        for threshold in [0,1.1,True,float('nan')]:
            with tempfile.TemporaryDirectory() as tmp:
                p.write_json(Path(tmp)/'config/policy_judging.json',{**STRATEGY,'threshold':threshold})
                with self.assertRaises(ValueError): c.load_strategy(tmp)

    def test_offline_export_uses_cascade_and_keeps_unresolved_cases_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p.write_json(root/'config/policies.json',REGISTRY)
            p.write_json(root/'config/policy_judging.json',STRATEGY)
            (root/'config/policy_rubric.md').write_text('rubric')
            (root/'config/policy_confidence.md').write_text('confidence')
            p.write_json(root/'data/roster.json',[{'id':'P','name':'Person','party':'Democrat','state':'CA','chamber':'house','status':'current'}])
            stmt={k:v for k,v in ITEM.items() if k in ('sid','text','date','context','url','source_type','verified_via')}
            p.write_json(root/'evidence/P.json',{'statements':[{**stmt,'verified':True}]})
            saved={}; save(saved,'deepseek',label('not_relevant',0.7)); save(saved,'astra',label('not_relevant',0.6))
            p.write_json(root/'data/policy_cascade.json',saved)
            result=p.build(root)
            self.assertEqual(result['members'][0]['policies'][ITEM['targets'][0]]['human_review'],1)
            self.assertEqual(result['members'][0]['policies'][ITEM['targets'][0]]['coverage'],'pending')
            chart=p.read_json(root/'site/data/policy_charts.json')
            self.assertEqual(chart['strategy']['threshold'],0.8)
            self.assertEqual(chart['policies'][ITEM['targets'][0]][0]['stance'],'review_required')
            detail=p.read_json(root/'site/data/policy_members/P.json')['policies'][ITEM['targets'][0]][0]
            self.assertEqual(detail['judges']['astra']['confidence'],0.6)
            self.assertEqual(detail['url'],ITEM['url'])

    def test_threshold_change_keeps_prior_astra_assessment_visible(self):
        saved={};save(saved,'deepseek',label('support',0.7));save(saved,'astra',label('oppose',0.95))
        r=c.resolve(ITEM,ITEM['targets'][0],saved,REGISTRY,'rubric','confidence',{**STRATEGY,'threshold':0.65})
        self.assertEqual(r['final_judge'],'deepseek')
        self.assertEqual(set(r['judges']),{'deepseek','astra'})
        self.assertTrue(r['model_disagreement'])

    def test_routing_reason_preserves_confidence_near_boundary(self):
        saved={};save(saved,'deepseek',label(confidence=0.7999))
        r=c.resolve(ITEM,ITEM['targets'][0],saved,REGISTRY,'rubric','confidence',STRATEGY)
        self.assertIn('0.7999',r['review_reason'])

    def test_astra_resolved_facet_difference_does_not_mark_summary_disputed(self):
        r={'stance':'support','strategy':'confidence_cascade','facet_disagreement':True,
           'review_status':'astra_reviewed','review_required':False,'model_disagreement':False}
        summary=p.summarize([r],1)
        self.assertEqual(summary['facet_disagreements'],0)
        self.assertEqual(summary['resolved_disagreements'],1)
        self.assertFalse(summary['review_required'])
