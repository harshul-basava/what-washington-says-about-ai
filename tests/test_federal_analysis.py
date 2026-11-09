import copy
import importlib
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FederalAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert (ROOT / 'federal_analysis.py').exists(), 'Federal broad analysis implementation is missing'
        cls.a = importlib.import_module('federal_analysis')

    def assessment(self, labels=None, topics=None, confidence=5):
        labels = labels or {}
        return {'labels': labels, 'confidence': {k: confidence for k in labels},
                'topics': topics or ['regulation']}

    def entry(self, labels=None, confidence=5):
        return {'assessments': {f'ds_{i}': {'value': self.assessment(labels, confidence=confidence)} for i in range(3)}, 'reference_scores': {}}

    def test_missing_statement_or_invalid_values_never_mean_silence(self):
        a=self.a
        valid={'statements': {'s1': self.assessment()}}
        self.assertEqual(a.parse_labels(json.dumps(valid), ['s1'])['s1']['labels'], {})
        for payload in [{'statements': {}}, {'statements': {'s1': self.assessment({'regulation': True})}},
                        {'statements': {'s1': self.assessment({'regulation': 5})}},
                        {'statements': {'s1': self.assessment(topics=['invented'])}}]:
            with self.subTest(payload=payload), self.assertRaises(ValueError):a.parse_labels(json.dumps(payload), ['s1'])

    def test_reviews_must_finish_before_a_score_can_be_accepted(self):
        a=self.a
        entry=self.entry({'x_risk':3})
        self.assertEqual(a.resolve_labels(entry)['status'],'pending')
        entry['assessments']['sol']={'value':self.assessment({'x_risk':0})}
        self.assertEqual(a.resolve_labels(entry)['status'],'pending')
        entry['assessments']['astra']={'value':self.assessment({'x_risk':2})}
        result=a.resolve_labels(entry)
        self.assertEqual(result['status'],'complete')
        self.assertEqual(result['a']['x_risk'],3)
        self.assertEqual(result['b']['x_risk'],2)
        self.assertEqual(a.resolve_labels(self.entry())['status'],'complete')

    def test_targeted_astra_review_changes_only_ai_overall_and_preserves_original_runs(self):
        entry=self.entry({'regulation':2})
        original=copy.deepcopy(entry['assessments'])
        entry['assessments']['astra_stance_review']={'model':'openai/gpt-6-astra','value':{
            'reviewed_dimension':'ai_overall','labels':{'ai_overall':3},'confidence':{'ai_overall':4},
            'reason':'A general statement of benefits.','supporting_quote':'AI benefits our whole economy.',
            'support_basis':'excerpt','review_id':'review-1'}}
        result=self.a.resolve_labels(entry)
        self.assertEqual(result['a'],{'regulation':2,'ai_overall':3})
        self.assertEqual(result['b'],{'regulation':2,'ai_overall':3})
        self.assertEqual(result['stance_review']['review_id'],'review-1')
        for key,value in original.items():self.assertEqual(entry['assessments'][key],value)

    def test_low_confidence_review_cannot_create_a_score(self):
        entry=self.entry()
        entry['assessments']['astra_stance_review']={'value':{
            'reviewed_dimension':'ai_overall','labels':{'ai_overall':3},'confidence':{'ai_overall':2},
            'reason':'Uncertain.', 'supporting_quote':'Perhaps AI helps.'}}
        result=self.a.resolve_labels(entry)
        self.assertNotIn('ai_overall',result['a'])
        self.assertNotIn('ai_overall',result['b'])

    def test_stance_audit_applies_idempotently_and_rejects_changed_evidence(self):
        import federal_stance_review as review
        a=self.a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root);config=a.configuration(root)
            ss=[{'sid':f's{i}','date':'2026-01-01','text':'AI will benefit our whole economy.',
                 'url':'https://example.gov/ai','verified':True,'source_type':'web',
                 'attribution':{'kind':'personal','speaker':'Official A'}} for i in range(1,4)]
            a.write(root/'evidence/executive_a.json',{'statements':ss})
            subjects,evidence=a.inputs(root);subject=next(s for s in subjects if s['id']=='executive_a');ss=evidence['executive_a']
            labels={'profiles':{'executive_a':{}}}
            for s in ss:
                labels['profiles']['executive_a'][s['sid']]={**self.entry(),
                    'input_hash':a.fingerprint(subject,[s],'labels',config)}
            a.write(root/a.LABEL_PATH,labels)
            a.write(root/a.PROFILE_PATH,{'profiles':{'executive_a':{
                'input_hash':a.fingerprint(subject,ss,'profile',config),'assessments':{}}}})
            result={'findings':[{'sid':'s1','label':3,'confidence':4,'reason':'Broad benefits.',
                                'supporting_quote':ss[0]['text'],'support_basis':'excerpt'}],
                    'no_stance_sids':['s2','s3'],'context_requests':[],'confidence':4,'reason':'One broad stance.',
                    'summary':{'status':'complete','text':'Expects broad benefits.','sids':['s1'],
                               'sentences':[{'text':'Expects broad benefits.','sids':['s1']}]}}
            audit={'model':review.MODEL,'target_ids':['executive_a'],'original_scores':{'executive_a':{'ai_overall':None}},
                   'profiles':{'executive_a':{'model':review.MODEL,'generation_id':'g1','assessed_at':'2026-11-09',
                        'evidence_hash':a.digest(ss),'contexts':{},'result':result}}}
            a.write(root/review.PATH,audit)
            review.apply(root)
            first=(root/a.LABEL_PATH).read_bytes();review.apply(root)
            self.assertEqual(first,(root/a.LABEL_PATH).read_bytes())
            entry=a.read(root/a.LABEL_PATH)['profiles']['executive_a']['s1']
            self.assertEqual(a.resolve_labels(entry)['a']['ai_overall'],3)
            self.assertIn('ds_0',entry['assessments'])
            ss[0]['text']='Changed evidence';a.write(root/'evidence/executive_a.json',{'statements':ss})
            with self.assertRaises(ValueError):review.apply(root)

    def test_regulation_requires_all_areas_and_real_source_ids(self):
        a=self.a
        value={'stances':{k:{'stance':0,'sids':[],'why':'No stance.'} for k in a.AREA_IDS}}
        self.assertEqual(len(a.parse_regulation(json.dumps(value), {'s1'}, a.AREA_IDS)),23)
        bad=copy.deepcopy(value);bad['stances'].pop(a.AREA_IDS[0])
        with self.assertRaises(ValueError):a.parse_regulation(json.dumps(bad), {'s1'}, a.AREA_IDS)
        bad=copy.deepcopy(value);bad['stances'][a.AREA_IDS[0]]={'stance':2,'sids':['s99'],'why':'Supports it.'}
        with self.assertRaises(ValueError):a.parse_regulation(json.dumps(bad), {'s1'}, a.AREA_IDS)

    def test_summary_needs_valid_citations(self):
        a=self.a
        for text in ['{"sentences":[]}', '{"sentences":[{"text":"Supports AI rules.","sids":["s9"]}]}']:
            with self.assertRaises(ValueError):a.parse_summary(text,{'s1'})
        row=a.parse_summary('{"sentences":[{"text":"Supports AI rules.","sids":["s1"]}]}',{'s1'})
        self.assertEqual(row['sids'],['s1'])

    def test_history_handles_partial_dates_and_unknown_dates(self):
        a=self.a
        self.assertEqual(a.date_end('2024'),'2024-12-31')
        self.assertEqual(a.date_end('2024-02'),'2024-02-29')
        self.assertIsNone(a.date_end(None))
        self.assertIsNone(a.date_end('2024-02-31'))
        statements=[{'sid':'s1','date':'2024-01-10'}, {'sid':'s2','date':'2024-01'}, {'sid':'s3','date':'2024'}, {'sid':'s4','date':None}]
        self.assertEqual([s['sid'] for s in a.at_cutoff(statements,'2024-01-31')],['s1','s2'])
        self.assertEqual([s['sid'] for s in a.at_cutoff(statements,'2024-12-31')],['s1','s2','s3'])

    def test_score_formula_matches_congress_and_pending_cannot_be_zero(self):
        a=self.a
        statements=[{'sid':f's{i}','date':'2025-01-01'} for i in range(1,4)]
        resolved={s['sid']:a.resolve_labels(self.entry({'regulation':2})) for s in statements}
        scores,details=a.score(statements,resolved,'2026-01-01')
        self.assertEqual(scores['regulation'],2)
        self.assertEqual(scores['x_risk'],0)
        self.assertEqual(details['x_risk']['reason_a'],'silent')
        resolved['s1']={'status':'pending'}
        self.assertTrue(all(v is None for v in a.score(statements,resolved,'2026-01-01')[0].values()))
        self.assertTrue(all(v is None for v in a.score(statements[:2],{},'2026-01-01')[0].values()))

    def test_regulation_disagreement_waits_for_independent_astra(self):
        a=self.a;areas={k:{'stance':0,'sids':[],'why':'No stance.'} for k in a.AREA_IDS}
        second=copy.deepcopy(areas);second['licensing']={'stance':2,'sids':['s1'],'why':'Supports licensing.'}
        entry={'assessments':{'reg_ds':{'value':areas},'reg_sol':{'value':second}}}
        self.assertEqual(a.resolve_regulation(entry)['status'],'pending')
        entry['assessments']['reg_astra']={'value':{'licensing':{'stance':1,'sids':['s1'],'why':'Calls for approval.'}}}
        result=a.resolve_regulation(entry)
        self.assertEqual(result['status'],'complete');self.assertEqual(result['areas']['licensing']['stance'],1)

    def test_context_hash_tracks_attribution_prompt_and_evidence_changes(self):
        a=self.a
        subject={'id':'exec_a','name':'Official A','entity_type':'person','roles':[]}
        statements=[{'sid':'s1','text':'AI needs rules.','date':'2026','url':'https://example.gov/a','attribution':{'kind':'personal'}}]
        first=a.fingerprint(subject,statements,'labels',{'rubric':'v1'})
        changed=copy.deepcopy(statements);changed[0]['attribution']['kind']='official_role'
        self.assertNotEqual(first,a.fingerprint(subject,changed,'labels',{'rubric':'v1'}))
        self.assertNotEqual(first,a.fingerprint(subject,statements,'labels',{'rubric':'v2'}))

    def fixture(self, root):
        from test_policy_subjects import PERSON, INSTITUTION, SUBJECTS
        a=self.a
        a.write(root/'config/policy_subjects.json',SUBJECTS)
        a.write(root/'data/roster.json',[])
        for name in ['federal_analysis.json','federal_analysis_prompt.md','rubric.md','reg_focus.md']:
            path=root/'config'/name;path.write_bytes((ROOT/'config'/name).read_bytes())
        a.write(root/'evidence/executive_a.json',{'statements':[]})
        a.write(root/'evidence/commerce.json',{'statements':[]})
        return PERSON,INSTITUTION

    def test_build_excludes_stale_profiles_and_does_not_write_congress(self):
        a=self.a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);person,institution=self.fixture(root)
            a.write(root/'config/federal_scope.json',{'version':1,'mode':'current_government','reviewed_on':'2026-11-09',
                'profiles':[{'subject_id':'commerce','decision':'include','reason':'Active','checked_on':'2026-11-09','source_url':'https://commerce.gov'}]})
            a.write(root/'site/data/federal_analysis/executive_a.json',{'id':'executive_a'})
            a.write(root/'data/scores.json',{'preserve':'Congress'})
            data=a.build(root,asof='2026-11-09')
            self.assertEqual([m['id'] for m in data['members']],['commerce'])
            self.assertEqual(data['members'][0]['status'],'no_evidence')
            self.assertFalse((root/'site/data/federal_analysis/executive_a.json').exists())
            self.assertEqual(a.read(root/'data/scores.json'),{'preserve':'Congress'})

    def test_observed_snapshots_remain_immutable(self):
        a=self.a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            a.build(root,asof='2026-11-09',record=True)
            before=(root/'data/federal_analysis_snapshots/2026-11-09.json').read_bytes()
            a.build(root,asof='2026-11-09',record=True)
            self.assertEqual((root/'data/federal_analysis_snapshots/2026-11-09.json').read_bytes(),before)

    def test_offline_build_never_invents_an_observed_snapshot(self):
        a=self.a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            for day in ['2026-11-08','2026-11-09']:
                a.build(root,asof=day)
                detail=a.read(root/'site/data/federal_analysis/commerce.json')
                self.assertFalse(any(h['kind']=='observed' for h in detail['history']))
            a.build(root,asof='2026-11-09',record=True)
            detail=a.read(root/'site/data/federal_analysis/commerce.json')
            self.assertEqual([h['date'] for h in detail['history'] if h['kind']=='observed'],['2026-11-09'])

    def test_chart_export_matches_eligible_profiles_and_revision(self):
        a=self.a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            data=a.build(root,asof='2026-11-09')
            charts=a.read(root/'site/data/federal_charts.json')
            self.assertIsNotNone(charts)
            self.assertEqual(charts['revision'],data['revision'])
            self.assertEqual(set(charts['profiles']),{m['id'] for m in data['members']})
            detail=a.read(root/'site/data/federal_analysis/commerce.json')
            self.assertEqual(charts['profiles']['commerce']['history'],detail['history'])

    def test_chart_topics_use_completed_labels_and_end_of_partial_dates(self):
        a=self.a
        statements=[{'sid':'day','date':'2024-02-01'}, {'sid':'month','date':'2024-02'},
                    {'sid':'year','date':'2024'}, {'sid':'unknown','date':None},
                    {'sid':'pending','date':'2024-02-01'}]
        resolved={s['sid']:{'status':'complete','topics':['regulation','copyright']} for s in statements}
        resolved['pending']={'status':'pending','topics':['regulation']}
        rows=a.chart_topics(statements,resolved)
        self.assertEqual([(r['date'],r['precision']) for r in rows],
                         [('2024-02-01','day'),('2024-02-29','month'),('2024-12-31','year')])
        self.assertEqual(rows[0]['topics'],['regulation','copyright'])

    def test_operational_settings_do_not_invalidate_paid_assessments(self):
        a=self.a
        config=a.configuration(ROOT);changed=copy.deepcopy(config)
        changed['settings']['daily_max_cost']=0.1
        changed['settings']['labels_batch_size']=40
        changed['settings']['history_start']='2024-01-31'
        subject={'id':'p','name':'P','roles':[]};ss=[{'sid':'s1','text':'AI matters.'}]
        self.assertEqual(a.fingerprint(subject,ss,'labels',config),a.fingerprint(subject,ss,'labels',changed))
        self.assertEqual(a.fingerprint(subject,ss,'profile',config),a.fingerprint(subject,ss,'profile',changed))

    def test_complete_profile_records_changes_while_another_is_pending(self):
        a=self.a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);person,institution=self.fixture(root);config=a.configuration(root)
            ss=[{'sid':f's{i}','date':'2026-01-01','text':'We support AI rules.','url':'https://example.gov/ai',
                'source_type':'web','verified':True,'attribution':{'kind':'personal','speaker':person['name']}} for i in range(1,4)]
            a.write(root/'evidence/executive_a.json',{'statements':ss})
            a.write(root/'evidence/commerce.json',{'statements':[{**ss[0],'attribution':{'kind':'institutional','speaker':institution['name'],'organization_id':'commerce'}}]})
            subjects,_=a.inputs(root);person=next(s for s in subjects if s['id']=='executive_a')
            cache={'profiles':{'executive_a':{}}}
            for s in ss:
                row=self.entry({'regulation':2});row['input_hash']=a.fingerprint(person,[s],'labels',config)
                for result in row['assessments'].values():result['model']='test'
                cache['profiles']['executive_a'][s['sid']]=row
            a.write(root/a.LABEL_PATH,cache)
            a.build(root,asof='2026-11-08',record=True)
            for row in cache['profiles']['executive_a'].values():
                for result in row['assessments'].values():result['value']['labels']['regulation']=3
            a.write(root/a.LABEL_PATH,cache)
            a.build(root,asof='2026-11-09',record=True)
            snapshot=a.read(root/'data/federal_analysis_snapshots/2026-11-09.json')
            self.assertIn('executive_a',snapshot);self.assertNotIn('commerce',snapshot)
            self.assertEqual(snapshot['executive_a']['scores']['regulation'],3)
            self.assertEqual(a.read(root/'data/federal_analysis_changes.json')[0]['new'],3)
