import copy
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'scripts/daily'), str(ROOT)]
from test_policy_subjects import PERSON, INSTITUTION, SUBJECTS
from policy_judgments import write_json
import policy_subjects

ACCOUNT = {'id':'official_a','subject_id':PERSON['id'],'handle':'OfficialA','kind':'personal',
           'source_url':'https://commerce.gov/official-a','verified_on':'2026-11-08',
           'valid_from':'2023-01-01','valid_until':None}
TEXT = 'We support strong export controls on advanced artificial intelligence chips to protect national security and prevent harmful military uses.'
POST = {'id':'100','text':TEXT,'created_at':'2026-11-01T12:00:00Z','author_id':'7','author':'OfficialA','is_repost':False,'is_promoted':False,'restricted':False}
PAGE = {'account':{'id':'7','username':'OfficialA'},'posts':[POST],'cursor':None}
CONFIG = {'version':1,'enabled':True,'since':'2023-01-01','page_limit':2,'max_seconds':120,
          'minimum_gap_seconds':20,'overlap_days':3,'accounts':[ACCOUNT]}

class XTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert (ROOT / 'scripts/federal_x.py').exists(), 'Federal X coordinator is missing'
        cls.x = importlib.import_module('federal_x')

    def fixture(self, root):
        write_json(root/'config/policy_subjects.json',SUBJECTS)
        write_json(root/'config/federal_x.json',CONFIG)
        write_json(root/'data/roster.json',[])
        for p in [PERSON,INSTITUTION]:
            write_json(root/f"evidence/{p['id']}.json",{'id':p['id'],'name':p['name'],'statements':[]})

    def test_month_windows_have_exclusive_ends_and_account_boundaries(self):
        self.assertEqual(self.x.windows('2024-01-20','2024-03-02'),[
            ('2024-01-20','2024-02-01'),('2024-02-01','2024-03-01'),('2024-03-01','2024-03-02')])

    def test_author_date_and_repost_checks_precede_attribution(self):
        s=self.x.statement(POST,ACCOUNT,PERSON,'7','2026-01-01','2026-11-09','2026-11-08')
        self.assertEqual(s['attribution']['kind'],'personal')
        self.assertEqual(s['date'],'2026-11-01')
        self.assertEqual(s['url'],'https://x.com/OfficialA/status/100')
        self.assertLessEqual(len(s['text'].split()),25)
        self.assertIn(s['text'],TEXT)
        for changes in [{'author_id':'8'},{'author':'SomeoneElse'},{'is_repost':True},{'is_promoted':True},
                        {'restricted':True},{'created_at':'2027-01-01T00:00:00Z'},{'created_at':'bad'},
                        {'text':'Nice story about completely unrelated issues.'}]:
            with self.subTest(changes=changes):
                self.assertIsNone(self.x.statement(POST|changes,ACCOUNT,PERSON,'7','2026-01-01','2026-11-09','2026-11-08'))

    def test_office_account_cannot_supply_a_different_officeholders_posts(self):
        a=ACCOUNT|{'kind':'official_role','role_index':0,'valid_from':'2025-01-20','valid_until':'2026-01-01'}
        self.assertIsNone(self.x.statement(POST,a,PERSON,'7','2023-01-01','2026-11-09','2026-11-08'))

    def test_search_resumes_the_same_window_and_appends_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            conf=copy.deepcopy(CONFIG);conf['page_limit']=1;write_json(root/'config/federal_x.json',conf)
            calls=[]
            def first(req):calls.append(req);return PAGE|{'cursor':'next'}
            r=self.x.collect(root,since='2026-11-01',client=first,now='2026-11-08')
            self.assertEqual(r['status'],'partial')
            def second(req):calls.append(req);return PAGE
            r=self.x.collect(root,client=second,now='2026-11-08')
            self.assertEqual(calls[1]['cursor'],'next')
            self.assertEqual(calls[1]['query'],calls[0]['query'])
            self.assertEqual(len(json.loads((root/f"evidence/{PERSON['id']}.json").read_text())['statements']),1)
            self.assertFalse((root/'data/new_statements.jsonl').exists())
            self.assertEqual(r['status'],'ok')

    def test_failure_never_advances_checkpoint_and_redacts_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            def failure(req):raise RuntimeError('credential=secret response body')
            r=self.x.collect(root,client=failure,now='2026-11-08')
            self.assertEqual(r['status'],'partial')
            state=(root/'data/federal_x_state.json').read_text()
            self.assertNotIn('secret',state+json.dumps(r))
            self.assertNotIn('last_success',state)

    def test_rate_limit_defers_later_searches_and_records_cooldown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            r=self.x.collect(root,client=lambda req:{'error':'rate_limited'},now='2026-11-08')
            self.assertEqual(r['error'],'rate_limited')
            self.assertTrue(json.loads((root/'data/federal_x_state.json').read_text())['retry_after'])

    def test_dry_run_and_missing_auth_do_not_collect(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
            r=self.x.collect(root,dry=True,now='2026-11-08')
            self.assertEqual(r['mapped_profiles'],1)
            self.assertEqual(r['unmapped_profiles'],1)
            self.assertEqual(before,{p:p.read_bytes() for p in root.rglob('*') if p.is_file()})
            with patch.dict(os.environ,{},clear=True):
                r=self.x.collect(root,now='2026-11-08')
            self.assertEqual(r['status'],'unavailable')
            self.assertEqual(r['error'],'missing_auth_token')
            self.assertFalse((root/'data/federal_x_state.json').exists())

    def test_repeated_cursor_and_changed_account_id_remain_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            r=self.x.collect(root,client=lambda req: PAGE|{'cursor':'same'},now='2026-11-08')
            self.assertEqual(r['status'],'partial')
            self.assertEqual(r['errors'][0]['error'],'repeated_cursor')
            r=self.x.collect(root,client=lambda req: PAGE|{'account':{'id':'9','username':'OfficialA'}},now='2026-11-08')
            self.assertEqual(r['errors'][0]['error'],'account_identity_changed')

    def test_registry_rejects_duplicate_handles_without_disjoint_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            conf=copy.deepcopy(CONFIG);conf['accounts'].append(ACCOUNT|{'id':'second'})
            write_json(root/'config/federal_x.json',conf)
            with self.assertRaises(ValueError):self.x.collect(root,dry=True,now='2026-11-08')

    def test_cursor_cycle_cannot_consume_every_future_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            config=copy.deepcopy(CONFIG);config['page_limit']=4;write_json(root/'config/federal_x.json',config)
            cursors=iter(['a','b','a',None])
            report=self.x.collect(root,client=lambda req:PAGE|{'cursor':next(cursors)},now='2026-11-08')
            self.assertEqual(report['status'],'partial')
            self.assertEqual(report['errors'][0]['error'],'repeated_cursor')

    def test_long_excerpt_is_an_exact_substring_and_stays_in_copyright_limit(self):
        text='Introductory words. '+TEXT+' '+('Additional details appear here. '*20)
        s=self.x.statement(POST|{'text':text},ACCOUNT,PERSON,'7','2026-01-01','2026-11-09','2026-11-08')
        self.assertTrue(s['excerpted'])
        self.assertIn(s['text'],text)
        self.assertEqual(len(s['text'].split()),25)

    def test_current_and_archived_account_mappings_remain_visible_without_auth(self):
        import federal_coverage
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            write_json(root/'data/federal_x_status.json',{'status':'unavailable','error':'missing_auth_token'})
            subjects=policy_subjects.load_subjects(root)
            report=federal_coverage.coverage(root,subjects,{})
            self.assertEqual(report['summary']['x_mapped_profiles'],1)
            self.assertEqual(report['summary']['x_statements'],0)
            self.assertEqual(report['profiles'][PERSON['id']]['x_status'],'unavailable')
            self.assertEqual(report['profiles'][INSTITUTION['id']]['x_status'],'unmapped')

    def test_registry_revision_does_not_leave_unreachable_pending_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            conf=copy.deepcopy(CONFIG);conf['page_limit']=1;write_json(root/'config/federal_x.json',conf)
            self.x.collect(root,client=lambda req:PAGE|{'cursor':'a'},now='2026-11-08')
            conf['accounts'][0]['verified_on']='2026-11-09';write_json(root/'config/federal_x.json',conf)
            report=self.x.collect(root,client=lambda req:PAGE,now='2026-11-09')
            self.assertEqual(report['pending_windows'],0)
            self.assertEqual(report['status'],'ok')
            import federal_coverage
            coverage=federal_coverage.coverage(root,policy_subjects.load_subjects(root),{})
            self.assertEqual(coverage['profiles'][PERSON['id']]['x_status'],'searched')

    def test_malformed_post_keeps_window_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            report=self.x.collect(root,client=lambda req:PAGE|{'posts':[{'id':'100'}]},now='2026-11-08')
            self.assertEqual(report['status'],'partial')
            self.assertEqual(report['errors'][0]['error'],'malformed_response')

    def test_old_pending_window_does_not_block_new_daily_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            self.x.collect(root,client=lambda req:{'error':'timeout'},now='2026-11-01')
            calls=[]
            def transport(req):calls.append(req);return PAGE|{'posts':[]}
            report=self.x.collect(root,client=transport,now='2026-11-08')
            self.assertEqual(report['status'],'ok')
            self.assertEqual(len(calls),2)
            self.assertTrue(any('until:2026-11-02' in r['query'] for r in calls))
            self.assertTrue(any('until:2026-11-09' in r['query'] for r in calls))

    def test_edited_post_does_not_append_a_second_excerpt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            self.x.collect(root,client=lambda req:PAGE,now='2026-11-08')
            edited=POST|{'text':'We now oppose the AI export controls because the proposed rules harm international cooperation and scientific research.'}
            self.x.collect(root,since='2026-11-01',client=lambda req:PAGE|{'posts':[edited]},now='2026-11-09')
            statements=json.loads((root/f"evidence/{PERSON['id']}.json").read_text())['statements']
            self.assertEqual(len(statements),1)
            self.assertEqual(statements[0]['text'],TEXT)

if __name__=='__main__':unittest.main()
