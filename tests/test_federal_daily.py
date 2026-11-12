import copy
import importlib.util
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/daily'))
import policy_judgments as policy
from test_policy_subjects import PERSON, INSTITUTION, SUBJECTS

QUOTE = 'We must enforce export controls on advanced artificial intelligence chips.'
CONTEXT = f'Commerce Secretary Official A said, “{QUOTE}”'
PAGE = {'url': 'https://commerce.gov/news/example', 'title': 'AI controls',
        'text': 'November 8, 2026. ' + CONTEXT, 'verified_via': 'exact_normalized_page_text'}
ROW = {'subject_id': 'executive_a', 'quote': QUOTE, 'attribution_quote': CONTEXT,
       'kind': 'official_role', 'role_index': 0, 'date': '2026-11-08', 'date_quote': 'November 8, 2026'}
CONFIG = {'version': 1, 'bootstrap_days': 14, 'overlap_days': 3, 'pages_per_group': 2,
          'collection_max_cost': 0.5, 'judgment_max_cost': 0.5,
          'groups': [{'id': 'commerce', 'name': 'Commerce', 'domains': ['commerce.gov'],
                      'queries': ['Commerce AI'], 'watch_urls': []}]}


class FederalTests(unittest.TestCase):
    def test_search_retrieval_is_a_lead_not_a_verified_source_snapshot(self):
        page={**PAGE,'verified_via':'exact_normalized_search_retrieval'}
        self.assertEqual(federal.validate_rows(page,[ROW],[PERSON],'2026-11-08'),([],1))

    def test_documented_speaker_conflict_blocks_only_the_reviewed_source(self):
        subject={**PERSON,'source_attribution_exclusions':[{'url':PAGE['url'],'reason':'Conflicting speaker labels','reviewed_on':'2026-11-12'}]}
        self.assertEqual(federal.validate_rows(PAGE,[ROW],[subject],'2026-11-08'),([],1))
        other={**PAGE,'url':'https://commerce.gov/news/other'}
        self.assertEqual(federal.validate_rows(other,[ROW],[subject],'2026-11-08')[1],0)

    def test_personal_quote_cannot_use_narration_as_its_own_attribution(self):
        narration = 'Commerce Secretary Official A supports American leadership in artificial intelligence.'
        page = {**PAGE, 'text': 'November 8, 2026. ' + narration}
        row = {**ROW, 'quote': narration, 'attribution_quote': narration}
        self.assertEqual(federal.validate_rows(page, [row], [PERSON], '2026-11-08'), ([], 1))
        # A surrounding speaker attribution still supports the actual direct words.
        self.assertEqual(federal.validate_rows(PAGE, [ROW], [PERSON], '2026-11-08')[1], 0)

    def test_same_source_quote_cannot_reenter_with_a_different_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            statement={'text':QUOTE,'url':PAGE['url'],'date':None,'verified':True}
            self.assertEqual(federal.append_evidence(root,'executive_a',[statement]),['s1'])
            self.assertEqual(federal.append_evidence(root,'executive_a',[{**statement,'url':PAGE['url']+'#quote','date':'2026-11-08'}]),[])
            self.assertEqual(federal.append_evidence(root,'executive_a',[{**statement,'url':'https://commerce.gov/news/later','date':'2026-11-09'}]),['s2'])

    @classmethod
    def setUpClass(cls):
        # A descriptive assertion also proves the new collector does not exist before implementation.
        assert (ROOT / 'scripts/daily/federal.py').exists(), 'Federal daily collector is missing'
        global federal, sources
        import federal
        import federal_sources as sources

    def fixture(self, root):
        policy.write_json(root / 'config/policy_subjects.json', SUBJECTS)
        policy.write_json(root / 'config/federal_sources.json', CONFIG)
        policy.write_json(root / 'data/roster.json', [])
        policy.write_json(root / 'evidence/executive_a.json', {'id': 'executive_a', 'name': PERSON['name'], 'statements': []})
        policy.write_json(root / 'evidence/commerce.json', {'id': 'commerce', 'name': INSTITUTION['name'], 'statements': []})

    def test_domains_require_a_hostname_boundary(self):
        self.assertTrue(sources.allowed_url(PAGE['url'], ['commerce.gov']))
        for url in ['https://evilcommerce.gov/news', 'https://commerce.gov.evil.test', 'file:///etc/passwd',
                    'https://commerce.gov@evil.test', 'https://commerce.gov:8080/news']:
            self.assertFalse(sources.allowed_url(url, ['commerce.gov']))

    def test_named_searches_use_only_current_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            policy.write_json(root/'config/federal_scope.json',{'version':1,'mode':'current_government',
                'reviewed_on':'2026-11-09','profiles':[
                    {'subject_id':'commerce','decision':'include','reason':'Active institution',
                     'checked_on':'2026-11-09','source_url':'https://commerce.gov'}]})
            config=copy.deepcopy(CONFIG);config['named_searches']=True
            config['groups'][0]['organization_ids']=['commerce','task_force']
            report=federal.collect(root,config,dry=True)
            self.assertEqual(report['groups']['commerce']['subject_ids'],['commerce'])
            subjects=federal.policy_subjects.load_subjects(root)
            queries=federal.search_groups(config,subjects)[0]['queries']
            self.assertFalse(any('Official A' in query for query in queries))

    def test_extraction_accepts_one_fenced_json_result_after_provider_prose(self):
        self.assertEqual(sources.parse_json('Here is the result:\n```json\n{"statements": []}\n```'), {'statements': []})
        with self.assertRaises(ValueError):
            sources.parse_json('```json\n{}\n```\n```json\n{}\n```')

    def test_date_anchor_cannot_invent_precision(self):
        self.assertEqual(federal.checked_date('2026-06', 'June 2026', 'Published June 2026', '2026-11-08'), '2026-06')
        self.assertEqual(federal.checked_date('2021-11', '2021 November', '2021 November', '2026-11-08'), '2021-11')
        with self.assertRaises(ValueError):
            federal.checked_date('2026-06-01', 'June 2026', 'Published June 2026', '2026-11-08')
        with self.assertRaises(ValueError):
            federal.checked_date('2021-11-01', '2021 November', '2021 November', '2026-11-08')

    def test_labeled_source_dates_preserve_exact_date_checks(self):
        for anchor in ('Publication Date: September 23, 2024', 'Date Published: September 23, 2024',
                       'Press Release | September 23, 2024', 'Release Date: September 23, 2024',
                       'FOR IMMEDIATE RELEASE | September 23, 2024', 'Released September 23, 2024'):
            with self.subTest(anchor=anchor):
                self.assertEqual(federal.checked_date('2024-09-23', anchor, anchor, '2026-11-08'), '2024-09-23')
                with self.assertRaises(ValueError):
                    federal.checked_date('2024-09-24', anchor, anchor, '2026-11-08')
        for anchor in ('Publication Date: September 2024', 'April 11 blog post',
                       'Updated September 23, 2024',
                       'Press Release | September 23, 2024 and October 1, 2024'):
            with self.subTest(anchor=anchor), self.assertRaises(ValueError):
                federal.checked_date('2024-09-23', anchor, anchor, '2026-11-08')

    def test_named_official_statement_heading_establishes_authorship(self):
        subject = {**PERSON, 'name': 'Lloyd Austin', 'aliases': ['Lloyd J. Austin III'],
                   'roles': [{**PERSON['roles'][0], 'title': 'Secretary of Defense'}]}
        heading = 'Secretary of Defense Lloyd J. Austin III Statement on the New Chief Digital and Artificial Intelligence Officer'
        self.assertTrue(federal.explicit_document_author(heading, subject))
        self.assertTrue(federal.explicit_document_author('Office of Commissioner Lloyd Austin Keynote Address Conference', subject))
        self.assertFalse(federal.explicit_document_author('Office of Commissioner Someone Else Keynote Address thanking Lloyd Austin', subject))
        for unrelated in ('Statement on Secretary of Defense Lloyd J. Austin III',
                          'Letter to Secretary of Defense Lloyd J. Austin III',
                          'Secretary of Defense Lloyd J. Austin III mentioned in remarks by another official'):
            self.assertFalse(federal.explicit_document_author(unrelated, subject))

    def test_canonical_institution_names_and_distinct_task_force(self):
        registry = json.loads((ROOT / 'config/policy_subjects.json').read_text())['subjects']
        for sid, name in [('caissi', 'CAISSI'), ('sisc', 'SISC'), ('si_task_force', 'Super Intelligence Force')]:
            subject = next(s for s in registry if s['id'] == sid)
            context = f'{name} stated: {QUOTE}'
            row = {**ROW, 'subject_id': sid, 'kind': 'institutional', 'attribution_quote': context}
            page = {**PAGE, 'text': 'November 8, 2026. ' + context}
            self.assertEqual(federal.validate_rows(page, [row], [subject], '2026-11-08')[1], 0)
        subject = next(s for s in registry if s['id'] == 'si_task_force')
        context = f'The Justice Department Super Intelligence Task Force stated: {QUOTE}'
        row = {**ROW, 'subject_id': 'si_task_force', 'kind': 'institutional', 'attribution_quote': context}
        self.assertEqual(federal.validate_rows({**PAGE, 'text': 'November 8, 2026. ' + context}, [row], [subject], '2026-11-08')[0], [])

    def test_exact_attribution_and_date_are_required(self):
        good, rejected = federal.validate_rows(PAGE, [ROW], [PERSON, INSTITUTION], '2026-11-08')
        self.assertEqual(rejected, 0)
        self.assertEqual(good[0][0], PERSON['id'])
        self.assertEqual(good[0][1]['attribution']['organization_id'], 'commerce')
        self.assertEqual(good[0][1]['date'], '2026-11-08')
        for changes in [{'quote': QUOTE.replace('enforce', 'oppose')},
                        {'attribution_quote': QUOTE}, {'date': '2026-11-09'},
                        {'date': '2026-01-01'}, {'role_index': 99},
                        {'subject_id': 'commerce', 'kind': 'personal'}]:
            with self.subTest(changes=changes):
                rows, rejected = federal.validate_rows(PAGE, [{**ROW, **changes}], [PERSON, INSTITUTION], '2026-11-08')
                self.assertEqual(rows, [])
                self.assertEqual(rejected, 1)

    def test_institution_requires_explicit_attribution_and_does_not_copy_to_people(self):
        quote = 'Commerce supports enforceable export controls on advanced artificial intelligence chips.'
        page = {**PAGE, 'text': quote}
        row = {'subject_id': 'commerce', 'quote': quote, 'attribution_quote': quote,
               'kind': 'institutional', 'date': None, 'date_quote': None}
        rows, rejected = federal.validate_rows(page, [row], [PERSON, INSTITUTION], '2026-11-08')
        self.assertEqual([pid for pid, _ in rows], ['commerce'])
        self.assertIsNone(rows[0][1]['date'])
        bad = {**row, 'quote': QUOTE, 'attribution_quote': QUOTE}
        self.assertEqual(federal.validate_rows({**PAGE, 'text': QUOTE}, [bad], [PERSON, INSTITUTION], '2026-11-08')[1], 1)

    def test_append_is_idempotent_preserves_old_ids_and_avoids_congress_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            statement = federal.validate_rows(PAGE, [ROW], [PERSON], '2026-11-08')[0][0][1]
            old = {**statement, 'sid': 's7', 'text': 'An older statement.', 'date': '2025'}
            path = root / 'evidence/executive_a.json'
            policy.write_json(path, {'statements': [old]})
            self.assertEqual(federal.append_evidence(root, 'executive_a', [statement]), ['s8'])
            self.assertEqual(federal.append_evidence(root, 'executive_a', [statement]), [])
            self.assertEqual(federal.append_evidence(root, 'executive_a', [{**statement, 'url': 'https://commerce.gov/archive'}]), [])
            self.assertEqual(json.loads(path.read_text())['statements'][0], old)
            self.assertFalse((root / 'data/new_statements.jsonl').exists())

    def test_dry_run_has_no_network_or_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            before = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            with patch.object(sources, 'Client', side_effect=AssertionError('network')):
                report = federal.collect(root, CONFIG, dry=True)
            self.assertEqual(report['status'], 'dry_run')
            self.assertEqual(before, {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_unavailable_x_does_not_skip_web_or_policy_judgments(self):
        import federal_x
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            with patch.object(federal,'collect',return_value={'status':'ok'}) as web, \
                 patch.object(federal_x,'collect',return_value={'status':'unavailable','error':'missing_auth_token'}) as x, \
                 patch.object(federal,'judge',return_value={'status':'ok'}) as judge, \
                 patch.object(federal,'build'),patch('llm.spent_this_month',return_value=0):
                report=federal.run(root,CONFIG)
            self.assertEqual(report['x']['error'],'missing_auth_token')
            self.assertEqual(report['judgments']['status'],'ok')
            self.assertEqual(report['status'],'partial')
            self.assertTrue(web.called and x.called and judge.called)

    def test_parallel_searches_save_each_result_on_the_coordinator_thread(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            config = copy.deepcopy(CONFIG)
            config['search_workers'] = 2
            config['groups'][0]['queries'] = ['first query', 'second query']
            barrier = threading.Barrier(2, timeout=2)
            def search(query, domains, since):
                barrier.wait()
                return [{**PAGE, 'url': PAGE['url'] + ('1' if query == 'first query' else '2')}]
            client = unittest.mock.Mock()
            client.search.side_effect = search
            client.page.side_effect = lambda page, domains: PAGE | {'url': page['url']}
            client.extract.return_value = []
            original_write = federal.write
            main_thread = threading.get_ident()
            def write(path, value):
                self.assertEqual(threading.get_ident(), main_thread)
                original_write(path, value)
            with patch.object(sources, 'Client', return_value=client), patch.object(federal, 'write', side_effect=write):
                report = federal.collect(root, config)
            self.assertEqual(report['errors'], [])
            state = federal.read(root / 'data/federal_state.json', {})
            self.assertEqual(len(state['queries']), 2)
            self.assertEqual(len(state['processed']), 2)

    def test_failed_page_stays_queued_and_successful_retry_does_not_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            client = unittest.mock.Mock()
            client.search.return_value = [PAGE]
            client.page.return_value = PAGE
            client.extract.side_effect = RuntimeError('provider failure')
            with patch.object(sources, 'Client', return_value=client), patch.object(federal, 'today', return_value='2026-11-08'):
                first = federal.collect(root, CONFIG)
                self.assertEqual(first['status'], 'partial')
                self.assertEqual(first['pending_pages'], 1)
                client.search.return_value = []
                client.extract.side_effect = None
                client.extract.return_value = [ROW]
                second = federal.collect(root, CONFIG)
                self.assertEqual(second['added'], {'executive_a': ['s1']})
                self.assertEqual(second['pending_pages'], 0)
                client.search.return_value = [PAGE]
                client.page.side_effect = AssertionError('Unchanged discovery must not use a page slot')
                third = federal.collect(root, CONFIG)
                self.assertEqual(third['added'], {})
                self.assertEqual(third['status'], 'ok')
            state = json.loads((root / 'data/federal_state.json').read_text())
            self.assertEqual(len(state['processed']), 1)
            self.assertNotIn(QUOTE, json.dumps(state))  # no full source pages published in state

    def test_search_failure_preserves_watermark_and_overflow_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            client = unittest.mock.Mock()
            client.search.side_effect = RuntimeError('search failure')
            policy.write_json(root / 'data/federal_state.json', {'groups': {'commerce': {'since': '2026-11-01'}}, 'pending': {}, 'processed': {}})
            with patch.object(sources, 'Client', return_value=client), patch.object(federal, 'today', return_value='2026-11-08'):
                report = federal.collect(root, CONFIG)
                self.assertEqual(report['status'], 'partial')
                state = json.loads((root / 'data/federal_state.json').read_text())
                self.assertEqual(state['groups']['commerce']['since'], '2026-11-01')
                client.search.side_effect = None
                client.search.return_value = [{**PAGE, 'url': PAGE['url'] + str(i)} for i in range(3)]
                client.page.side_effect = lambda page, domains: page
                client.extract.return_value = []
                report = federal.collect(root, CONFIG)
                self.assertEqual(report['pending_pages'], 1)
                self.assertEqual(report['status'], 'partial')

    def test_changed_page_is_reprocessed_and_no_quote_matches_are_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            client = unittest.mock.Mock()
            client.search.return_value = [PAGE]
            client.page.side_effect = lambda page, domains: page
            client.extract.return_value = []
            with patch.object(sources, 'Client', return_value=client), patch.object(federal, 'today', return_value='2026-11-08'):
                federal.collect(root, CONFIG)
                client.search.return_value = [{**PAGE, 'text': PAGE['text'] + ' Updated statement.'}]
                client.extract.return_value = [ROW]
                result = federal.collect(root, CONFIG, since='2026-11-08')
            self.assertEqual(result['added'], {'executive_a': ['s1']})

    def test_long_page_resumes_after_budget_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            page = {**PAGE, 'text': PAGE['text'] + (' filler' * 5000) + ' Official A discusses more AI policy.'}
            client = unittest.mock.Mock()
            client.search.return_value = [page]
            client.page.return_value = page
            client.extract.side_effect = [[ROW], RuntimeError('budget exhausted')]
            with patch.object(sources, 'Client', return_value=client), patch.object(federal, 'today', return_value='2026-11-08'):
                first = federal.collect(root, CONFIG)
                self.assertEqual(first['added'], {'executive_a': ['s1']})
                self.assertEqual(first['pending_pages'], 1)
                state = json.loads((root / 'data/federal_state.json').read_text())
                self.assertEqual(state['pending'][page['url']]['next_chunk'], 1)
                client.extract.side_effect = None
                client.extract.return_value = []
                second = federal.collect(root, CONFIG)
            self.assertEqual(second['pending_pages'], 0)
            self.assertEqual(len(json.loads((root / 'evidence/executive_a.json').read_text())['statements']), 1)

    def test_query_checkpoints_prevent_budget_starvation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            config = copy.deepcopy(CONFIG)
            config['groups'] = [{**CONFIG['groups'][0], 'id': 'a', 'queries': ['a1', 'a2']},
                                {**CONFIG['groups'][0], 'id': 'b', 'queries': ['b1']}]
            successful = []
            for _ in range(3):
                client = unittest.mock.Mock(); calls = []
                def search(query, domains, since):
                    if calls:
                        raise RuntimeError('budget exhausted')
                    calls.append(query); successful.append(query); return []
                client.search.side_effect = search
                with patch.object(sources, 'Client', return_value=client), patch.object(federal, 'today', return_value='2026-11-08'):
                    federal.collect(root, config)
            self.assertEqual(successful, ['a1', 'a2', 'b1'])

    def test_query_checkpoint_saves_its_discovered_pages_before_next_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            config = copy.deepcopy(CONFIG); config['groups'][0]['queries'] = ['first', 'second']
            client = unittest.mock.Mock(); client.search.side_effect = [[PAGE], SystemExit('interrupted')]
            with patch.object(sources, 'Client', return_value=client):
                with self.assertRaises(SystemExit):
                    federal.collect(root, config)
            state = federal.read(root / 'data/federal_state.json', {})
            self.assertIn(PAGE['url'], state['pending'])
            self.assertEqual(len(state['queries']), 1)

    def test_federal_run_still_judges_and_builds_after_collection_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            with patch.object(federal, 'collect', side_effect=RuntimeError('network')), \
                 patch.object(federal, 'judge', return_value={'status': 'ok', 'pending_pairs': 0}), \
                 patch.object(federal, 'build', return_value=None):
                report = federal.run(root, CONFIG)
            self.assertEqual(report['status'], 'partial')
            self.assertEqual(report['judgments']['status'], 'ok')
            self.assertTrue((root / 'data/federal_status.json').exists())

    def test_daily_routing_runs_federal_after_congress_failure_and_selects_sources(self):
        spec = importlib.util.spec_from_file_location('daily_runner_test', ROOT / 'scripts/daily/run.py')
        daily = importlib.util.module_from_spec(spec); spec.loader.exec_module(daily)
        with patch.object(daily, 'run_congress', side_effect=RuntimeError('Congress failed')), \
             patch.object(federal, 'main', return_value={'status': 'ok'}) as update:
            with self.assertRaises(RuntimeError):
                daily.main(['--sources', 'web,federal'])
            update.assert_called_once()
        with patch.object(daily, 'run_congress', side_effect=AssertionError('Congress must not run')), \
             patch.object(federal, 'main', return_value={'status': 'dry_run'}):
            self.assertEqual(daily.main(['--sources', 'federal', '--dry-run'])['federal']['status'], 'dry_run')

    def test_daily_federal_runs_first_and_does_not_prevent_congress_on_failure(self):
        spec = importlib.util.spec_from_file_location('daily_order_test', ROOT / 'scripts/daily/run.py')
        daily = importlib.util.module_from_spec(spec); spec.loader.exec_module(daily)
        calls = []
        def federal_work(args):
            calls.append('federal')
            raise ValueError('bad config')
        def congress_work(args):
            calls.append('congress')
            return {}
        with patch.object(daily, 'run_congress', side_effect=congress_work), patch.object(federal, 'main', side_effect=federal_work):
            with self.assertRaises(ValueError):
                daily.main(['--sources', 'web,federal'])
        self.assertEqual(calls, ['federal', 'congress'])


if __name__ == '__main__':
    unittest.main()

class FederalAnalysisDailyTests(unittest.TestCase):
    def test_policy_and_broad_analysis_share_the_model_allowance(self):
        import federal
        import federal_analysis_models
        import llm
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'config').mkdir()
            (root/'config/federal_analysis.json').write_text('{}')
            with patch.object(federal,'judge',return_value={'status':'ok'}), \
                 patch.object(federal,'build',return_value=None), \
                 patch.object(llm,'spent',side_effect=[10.0,10.0,10.2]), \
                 patch.object(federal_analysis_models,'run',return_value={'status':'ok'}) as analysis:
                report=federal.run(root,CONFIG,skip_collect=True)
            self.assertEqual(report['analysis']['status'],'ok')
            self.assertAlmostEqual(analysis.call_args.kwargs['max_cost'],0.3)
            self.assertTrue(analysis.call_args.kwargs['daily'])

    def test_judgment_pipelines_rotate_without_adding_budget(self):
        import federal
        import federal_analysis_models
        import llm
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'config').mkdir()
            (root/'config/federal_analysis.json').write_text('{}')
            ledger=[10.0];calls=[]
            def policy_run(root,max_cost,dry=False):
                calls.append(('judgments',round(max_cost,4)))
                ledger[0]+=max_cost
                return {'status':'partial'}
            def analysis_run(root,max_cost,**kwargs):
                calls.append(('analysis',round(max_cost,4)))
                ledger[0]+=max_cost
                return {'status':'partial'}
            with patch.object(federal,'judge',side_effect=policy_run), \
                 patch.object(federal,'build',return_value=None), \
                 patch.object(llm,'spent',side_effect=lambda *args:ledger[0]), \
                 patch.object(federal_analysis_models,'run',side_effect=analysis_run):
                federal.run(root,CONFIG,skip_collect=True)
                federal.run(root,CONFIG,skip_collect=True)
            self.assertEqual(calls,[('judgments',0.5),('analysis',0),('analysis',0.5),('judgments',0)])
            self.assertAlmostEqual(ledger[0],11.0)
            scheduler=root/'data/federal_judgment_scheduler.json'
            before=scheduler.read_text()
            with patch.object(federal,'judge',return_value={'status':'dry_run'}), \
                 patch.object(federal_analysis_models,'run',return_value={'status':'dry_run'}):
                federal.run(root,CONFIG,skip_collect=True,dry=True)
            self.assertEqual(scheduler.read_text(),before)


    def policy_fixture(self, root):
        from test_policy_cascade import STRATEGY
        from test_policy_judgments import REGISTRY
        FederalTests().fixture(root)
        policy.write_json(root / 'config/policies.json', REGISTRY)
        policy.write_json(root / 'config/policy_judging.json', STRATEGY)
        (root / 'config/policy_rubric.md').write_text('rubric')
        (root / 'config/policy_confidence.md').write_text('confidence')
        return REGISTRY, STRATEGY

    def policy_evidence(self, root, subject, count):
        from test_policy_judgments import ITEM
        attribution = {'kind': 'personal', 'speaker': subject['name']}
        if subject['entity_type'] == 'institution':
            attribution.update(kind='institutional', organization_id=subject['id'])
        policy.write_json(root / 'evidence' / f"{subject['id']}.json", {'statements': [
            {**ITEM, 'sid': f's{i}', 'text': f"{ITEM['text']} Excerpt {i}.", 'verified': True, 'attribution': attribution}
            for i in range(1, count + 1)
        ]})

    def test_real_daily_judge_reports_pending_pairs_at_zero_allowance(self):
        import federal
        import phase3_policies as runner
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.policy_fixture(root)
            self.policy_evidence(root, PERSON, 1)
            with patch.object(runner, 'label_cascade', side_effect=AssertionError('No label call at zero allowance')), \
                 patch.object(runner, 'label', side_effect=AssertionError('No label call at zero allowance')):
                report = federal.judge(root, max_cost=0)
            self.assertEqual(report['status'], 'partial')
            self.assertEqual(report['candidate_statements'], 1)
            self.assertEqual(report['pending_pairs'], 1)
            self.assertEqual(report['incomplete_batches'], 0)
            self.assertEqual(report['review_counts'], {'awaiting_deepseek': 1})
            self.assertEqual(list((root / 'data').iterdir()), [root / 'data/roster.json'])

    def test_daily_policy_rotation_reaches_later_agency_and_review_backlog(self):
        import contextlib
        import io
        from types import SimpleNamespace
        import federal
        import llm
        import phase3_policies as runner
        import policy_cascade as cascade
        from test_policy_cascade import label
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry, strategy = self.policy_fixture(root)
            late = {**INSTITUTION, 'id': 'z_agency', 'name': 'Later Agency'}
            policy.write_json(root / 'config/policy_subjects.json', {**SUBJECTS, 'subjects': [*SUBJECTS['subjects'], late]})
            self.policy_evidence(root, PERSON, 1)
            self.policy_evidence(root, late, 1)
            target = 'kill_switch_act_119'
            prior = next(item for item in policy.candidates(root, registry) if item['person_id'] == PERSON['id'])
            saved_path = root / 'data/policy_cascade.json'
            saved = {'schema_version': 1, 'results': {}}
            cascade.save_result(saved, prior, target, 'deepseek', label(confidence=0.7), registry, 'rubric', 'confidence', strategy, 'seed')
            policy.write_json(saved_path, saved)
            metadata = {'data': [{'id': model, 'pricing': {'prompt': '0', 'completion': '0', 'request': '1'}}
                                 for model in cascade.models(strategy).values()]}
            meta = SimpleNamespace(raise_for_status=lambda: None, json=lambda: metadata)
            ledger = []
            calls = []
            def chat(messages, **kwargs):
                role = kwargs['tag'].removeprefix('daily_policy_cascade_')
                batch = json.loads(messages[1]['content'].split('\n', 1)[1])
                self.assertEqual(len(batch), 1)
                item = batch[0]
                key = item['key']
                ledger.append(1)
                calls.append((role, key))
                value = {}
                if key != 'commerce|s1':
                    value = {'judgments': [{'key': key, 'targets': {
                        target: label(confidence=0.7 if key == 'z_agency|s1' and role == 'deepseek' else 0.9)
                    }}]}
                if role == 'astra':
                    primary = policy.read_json(saved_path)['results'][key][target]['deepseek']['label']
                    self.assertLess(primary['confidence'], strategy['threshold'])
                return {'id': 'fake-generation', 'usage': {'cost': 1}, 'choices': [{'message': {'content': json.dumps(value)}}]}
            with patch.object(runner, 'ROOT', root / 'manual-root'), patch.dict(llm.os.environ, {'OPENROUTER_API_KEY': 'test'}), \
                 patch.object(llm, 'BUDGETS', {'openrouter': 100, 'monthly': {'openrouter': 100}}), \
                 patch.object(llm, 'spent', side_effect=lambda _: sum(ledger)), \
                 patch.object(llm, 'spent_this_month', side_effect=lambda _: sum(ledger)), \
                 patch.object(llm, '_log', side_effect=lambda provider, cost, tag, metadata: ledger.append(cost)), \
                 patch.object(llm, 'chat', side_effect=chat), patch.object(llm.httpx, 'get', return_value=meta) as get, \
                 contextlib.redirect_stdout(io.StringIO()):
                for day in range(12):
                    self.policy_evidence(root, INSTITUTION, day + 2)
                    before = sum(ledger)
                    report = federal.judge(root, max_cost=1.01)
                    self.assertLessEqual(sum(ledger) - before, 1.01)
            results = policy.read_json(saved_path)['results']
            self.assertIn('astra', results[prior['key']][target])
            self.assertIn('astra', results['z_agency|s1'][target])
            self.assertIn('deepseek', results['commerce|s2'][target])
            self.assertNotIn('commerce|s1', results)
            self.assertGreaterEqual(calls.count(('deepseek', 'commerce|s1')), 2)
            self.assertEqual(report['status'], 'partial')
            self.assertGreater(report['pending_pairs'], 0)
            self.assertEqual(get.call_count, 12)
            self.assertFalse((root / 'manual-root').exists())
            cursor = root / 'data/federal_policy_scheduler.json'
            before = cursor.read_bytes()
            with patch.object(runner, 'label', side_effect=AssertionError('No label call in dry run')):
                dry_report = federal.judge(root, max_cost=1.01, dry=True)
            self.assertEqual(dry_report['status'], 'dry_run')
            self.assertEqual(dry_report['pending_pairs'], report['pending_pairs'])
            self.assertEqual(cursor.read_bytes(), before)
