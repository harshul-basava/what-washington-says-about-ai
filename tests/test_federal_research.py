import copy
import sys
import tempfile
import unittest
import threading
import io
from types import SimpleNamespace
from unittest.mock import Mock, patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'scripts/daily')]
from test_federal_daily import CONTEXT, PAGE, PERSON, QUOTE, ROW
import federal


class HistoricalTests(unittest.TestCase):
    def test_research_coverage_excludes_duplicate_counts_and_dates(self):
        import federal_coverage
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);old={'sid':'s1','text':QUOTE,'url':PAGE['url'],'date':'2025','verified':True}
            federal.write(root/'evidence'/f"{PERSON['id']}.json",{'statements':[old,{**old,'sid':'s2','date':'2026','duplicate_of':'s1'}]})
            profile=federal_coverage.coverage(root,[PERSON],{})['profiles'][PERSON['id']]
            self.assertEqual(profile['statements'],1)
            self.assertEqual(profile['latest_date'],'2025')

    def test_official_document_author_can_support_distant_speech_quote(self):
        header = 'Remarks by Commerce Secretary Official A'
        page = {**PAGE, 'text': header + ' November 8, 2026. ' + ('Introductory text. ' * 300) + QUOTE}
        row = {**ROW, 'attribution_quote': header, 'attribution_basis': 'document_author'}
        valid, rejected = federal.validate_rows(page, [row], [PERSON], '2026-11-08')
        self.assertEqual(rejected, 0)
        self.assertEqual(valid[0][1]['text'], QUOTE)
        self.assertEqual(valid[0][1]['attribution']['basis'], 'document_author')
        for changes in [{'url': 'https://news.example/article'}, {'text': page['text'].replace('Remarks by', 'Meeting with')}]:
            self.assertEqual(federal.validate_rows({**page, **changes}, [row], [PERSON], '2026-11-08')[0], [])
        testimony = {**page, 'url': 'https://docs.house.gov/meetings/HHRG-119-Wstate-OfficialA.pdf',
                     'text': 'Secretary Official A November 8, 2026. ' + ('Introductory text. ' * 300) + QUOTE}
        witness = {**row, 'attribution_quote': 'Secretary Official A'}
        self.assertEqual(federal.validate_rows(testimony, [witness], [PERSON], '2026-11-08')[1], 0)

    def test_research_helpers_block_private_sources_and_limit_quotation(self):
        import federal_research as research
        self.assertTrue(research.public_url('https://www.nist.gov/news'))
        for url in ['https://127.0.0.1/x', 'https://localhost/x', 'https://10.0.0.1/', 'file:///etc/passwd', 'https://user:pass@nist.gov/']:
            self.assertFalse(research.public_url(url))
        first = {'text': ' '.join(['one'] * 20), 'url': 'https://news.example/a'}
        second = {'text': ' '.join(['two'] * 8), 'url': first['url']}
        accepted, rejected = research.limit_quotes([first, second], {})
        self.assertEqual(accepted, [first]); self.assertEqual(rejected, 1)
        official = {**second, 'url': 'https://www.nist.gov/a'}
        self.assertEqual(research.limit_quotes([official] * 4, {})[1], 0)

    def test_pdf_text_and_overlap_deduplication(self):
        import federal_research as research
        long = {'text': QUOTE + ' We will work with our allies.', 'date': '2026-11-08'}
        self.assertTrue(research.overlaps({'text': QUOTE, 'date': long['date']}, [long]))
        self.assertFalse(research.overlaps({'text': QUOTE, 'date': '2025'}, [long]))

    def test_source_context_recovery_never_changes_a_quote(self):
        import federal_research as research
        row = {**ROW, 'attribution_quote': 'Official A said: ' + QUOTE}
        page = {**PAGE, 'text': 'November 8, 2026. Commerce Secretary Official A said the following. ' + QUOTE}
        fixed = research.source_context(row, page, PERSON)
        self.assertEqual(fixed['quote'], QUOTE)
        self.assertIn(fixed['attribution_quote'], page['text'])
        self.assertEqual(federal.validate_rows(page, [fixed], [PERSON], '2026-11-08')[1], 0)

    def test_explicit_author_header_can_repair_an_omitted_basis(self):
        import federal_research as research
        header = 'Remarks by Commerce Secretary Official A'
        page = {**PAGE, 'text': header + ' November 8, 2026. ' + ('Introduction. ' * 500) + QUOTE}
        row = {**ROW, 'attribution_quote': header}
        row.pop('attribution_basis', None)
        fixed = research.source_context(row, page, PERSON)
        self.assertEqual(fixed.get('attribution_basis'), 'document_author')
        self.assertEqual(fixed['quote'], row['quote'])
        self.assertEqual(federal.validate_rows(page, [fixed], [PERSON], '2026-11-08')[1], 0)
        self.assertNotEqual(research.source_context(row, {**page, 'url': 'https://news.example/speech'}, PERSON).get('attribution_basis'), 'document_author')

    def test_government_weekday_date_and_middle_initial(self):
        self.assertEqual(federal.checked_date('2026-11-08', 'Sunday, November 8, 2026',
                                              'Sunday, November 8, 2026', '2026-11-08'), '2026-11-08')
        self.assertTrue(federal.contains_name('Official J. A spoke.', PERSON))
        self.assertFalse(federal.contains_name('Official Jones A spoke.', PERSON))
        page = {**PAGE, 'text': PAGE['text'].replace('November 8, 2026', 'November 08, 2026')}
        valid, rejected = federal.validate_rows(page, [ROW], [PERSON], '2026-11-08')
        self.assertEqual(rejected, 0)
        self.assertEqual(valid[0][1]['date_quote'], 'November 08, 2026')

    def test_research_progress_uses_the_nested_pass_registry(self):
        import federal_research as research
        audit = {'profiles': {}}
        entry = {'status': 'completed', 'added_sids': ['s1']}
        research.record_pass(audit, 'person', 3, entry)
        self.assertEqual(audit['profiles']['person']['passes']['3'], entry)

    def test_dotted_month_dates_preserve_the_exact_source_anchor(self):
        for anchor, day in [('Nov. 8, 2026', '2026-11-08'), ('Sept. 9, 2025', '2025-09-09')]:
            page = {**PAGE, 'text': anchor + '. ' + CONTEXT}
            row = {**ROW, 'date': day, 'date_quote': anchor}
            valid, rejected = federal.validate_rows(page, [row], [PERSON], '2026-11-08')
            self.assertEqual(rejected, 0)
            self.assertEqual(valid[0][1]['date_quote'], anchor)
            self.assertEqual(valid[0][1]['date'], day)

    def test_prepared_delivery_header_identifies_a_government_speech_author(self):
        header = 'Remarks as Prepared for Delivery by Commerce Secretary Official A'
        page = {**PAGE, 'text': header + ' November 8, 2026. ' + ('Introductory text. ' * 300) + QUOTE}
        row = {**ROW, 'attribution_quote': header, 'attribution_basis': 'document_author'}
        valid, rejected = federal.validate_rows(page, [row], [PERSON], '2026-11-08')
        self.assertEqual(rejected, 0)
        self.assertEqual(valid[0][1]['text'], QUOTE)
        self.assertEqual(federal.validate_rows({**page, 'url': 'https://news.example/article'}, [row], [PERSON], '2026-11-08')[0], [])

    def test_explicit_government_memo_and_testimony_authorship_headers(self):
        headers = ['Statement for the Record Commerce Secretary Official A',
                   'FROM: Commerce Secretary Official A',
                   'Prepared by: Commerce Secretary Official A',
                   'As Delivered by Commerce Secretary Official A',
                   'Official A, Commerce Secretary, Delivers Remarks at the AI Summit',
                   'Official A, Commerce Secretary. Testimony before the Senate.']
        for header in headers:
            with self.subTest(header=header):
                page = {**PAGE, 'text': header + ' November 8, 2026. ' + ('Introductory text. ' * 300) + QUOTE}
                row = {**ROW, 'attribution_quote': header, 'attribution_basis': 'document_author'}
                self.assertEqual(federal.validate_rows(page, [row], [PERSON], '2026-11-08')[1], 0)
        for header in ['Prepared for Commerce Secretary Official A',
                       'Remarks for the AI Summit. Prepared for Commerce Secretary Official A',
                       'Commerce Secretary Official A',
                       'Attendees: Commerce Secretary Official A. Testimony before the Senate.',
                       'FROM: Jane Smith TO: Commerce Secretary Official A',
                       'Statement for the Record Jane Smith TO: Commerce Secretary Official A',
                       'As Delivered by Jane Smith TO: Commerce Secretary Official A',
                       'Remarks by Jane Smith to Commerce Secretary Official A',
                       'Official A introduces Jane Smith, who delivers remarks at the summit.']:
            page = {**PAGE, 'text': header + ' November 8, 2026. ' + QUOTE}
            row = {**ROW, 'attribution_quote': header, 'attribution_basis': 'document_author'}
            self.assertEqual(federal.validate_rows(page, [row], [PERSON], '2026-11-08')[0], [])

    def test_one_json_object_after_provider_prose(self):
        import federal_sources
        self.assertEqual(federal_sources.parse_json('A source gap. {"statements": []}'), {'statements': []})
        with self.assertRaises(ValueError):
            federal_sources.parse_json('Result: {} {}')

    def test_research_coverage_reports_people_separately(self):
        import federal_research as research
        subjects = [PERSON, {**PERSON, 'id': 'institution', 'entity_type': 'institution'}]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for subject, n in zip(subjects, [2, 10]):
                federal.write(root / 'evidence' / (subject['id'] + '.json'), {'statements': [
                    {'text': QUOTE, 'url': f'https://nist.gov/{i}', 'date': '2025', 'verified': True} for i in range(n)]})
            result = research.coverage(root, subjects, {})
            self.assertEqual(result['summary']['people_median_statements'], 2)
            self.assertEqual(result['summary']['unique_source_pages'], 10)
            self.assertEqual(result['profiles'][PERSON['id']]['research_status'], 'not_started')

    def test_daily_named_searches_cover_every_federal_profile(self):
        import json
        import policy_subjects
        subjects = [s for s in policy_subjects.load_subjects(ROOT) if s['branch'] == 'executive']
        config = json.loads((ROOT / 'config/federal_sources.json').read_text())
        groups = federal.search_groups(config, subjects)
        assigned = [pid for g in groups for pid in g['subject_ids']]
        self.assertEqual(sorted(assigned), sorted(s['id'] for s in subjects))
        for subject in subjects:
            group = next(g for g in groups if subject['id'] in g['subject_ids'])
            self.assertTrue(any(subject['name'] in q for q in group['queries']))

    def test_daily_group_order_prioritizes_previous_failures(self):
        groups = [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}]
        state = {'groups': {'a': {'since': '2026-11-08'}, 'b': {'since': '2026-11-06'}}}
        self.assertEqual([g['id'] for g in federal.fair_groups(groups, state)], ['c', 'b', 'a'])

    def test_pdf_source_text_is_verified_from_the_download(self):
        import federal_sources as sources
        import httpx
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        writer = PdfWriter(); page = writer.add_blank_page(width=600, height=800)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        stream = DecodedStreamObject(); stream.set_data(('BT /F1 12 Tf 10 700 Td (' + PAGE['text'] + ') Tj ET').encode('latin1', errors='replace'))
        page[NameObject('/Contents')] = writer._add_object(stream)
        out = io.BytesIO(); writer.write(out)
        response = httpx.Response(200, content=out.getvalue(), request=httpx.Request('GET', PAGE['url']))
        client = sources.Client.__new__(sources.Client)
        with patch.object(sources.httpx, 'get', return_value=response):
            result = client.page({'url': PAGE['url']}, ['commerce.gov'])
        self.assertIn(QUOTE, result['text'])
        self.assertEqual(result['verified_via'], 'exact_normalized_page_text')

    def test_concurrent_reservations_prevent_overspending(self):
        import federal_sources as sources
        client = sources.Client.__new__(sources.Client)
        started, release = threading.Event(), threading.Event()
        ledger = []
        def chat(*args, **kwargs):
            started.set(); release.wait(5); return {'usage': {'cost': 0}}
        class BudgetError(Exception): pass
        client.llm = SimpleNamespace(spent=lambda _: sum(ledger), spent_this_month=lambda _: 999,
            _log=lambda provider, amount, tag, meta: ledger.append(amount),
            BUDGETS={'openrouter': 10, 'monthly': {'openrouter': 1}}, BudgetExceeded=BudgetError, chat=chat)
        client.metadata = {'pricing': {'prompt': '.001', 'completion': '.001'}}
        client.daily = False; client.model = 'test'
        from model_budget import Budget
        client.budget = Budget(.3, False, {'test': client.metadata}, client.llm)
        thread = threading.Thread(target=client.chat, args=([{'role': 'user', 'content': 'a'}], 'test', 10))
        thread.start(); self.assertTrue(started.wait(2))
        try:
            with self.assertRaises(BudgetError):
                client.chat([{'role': 'user', 'content': 'a'}], 'test', 10)
        finally:
            release.set(); thread.join()
        self.assertAlmostEqual(client.llm.spent('openrouter'), 0)

    def test_cached_research_resume_never_repeats_paid_search(self):
        import federal_research as research
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); directory = root / 'data/raw/federal_research' / PERSON['id']
            federal.write(root / 'evidence' / f"{PERSON['id']}.json", {'statements': []})
            (root / 'config').mkdir(); (root / 'config/federal_research_prompt.md').write_text('Research')
            raw = {'choices': [{'message': {'content': __import__('json').dumps({'statements': [{**ROW, 'url': PAGE['url']}], 'gaps': []}), 'annotations': []}}], 'usage': {'cost': .1, 'server_tool_use_details': {'web_search_requests': 1}}}
            federal.write(directory / 'pass-1.json', raw)
            client = Mock(model='test'); client.page.return_value = PAGE
            for _ in range(2):
                research.research_one(root, PERSON, [], client, {}, 1, threading.Lock(), {})
            client.chat.assert_not_called()
            self.assertEqual(len(federal.read(root / 'evidence' / f"{PERSON['id']}.json", {})['statements']), 1)

    def test_seed_research_checks_official_pages_and_resumes(self):
        import federal_research as research
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            federal.write(root / 'evidence' / f"{PERSON['id']}.json", {'statements': []})
            client = Mock(model='test'); client.page.return_value = PAGE; client.extract.return_value = [ROW]
            seeds = [{'url': PAGE['url']}, {'url': 'https://news.example/article'}]
            first = research.seed_one(root, PERSON, seeds, client)
            second = research.seed_one(root, PERSON, seeds, client)
            self.assertEqual(first['added_sids'], ['s1'])
            self.assertEqual(second['added_sids'], ['s1'])
            client.page.assert_called_once(); client.extract.assert_called_once()

    def test_seed_failure_records_source_or_model_stage(self):
        import federal_research as research
        for stage in ('source_fetch', 'extract'):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                federal.write(root / 'evidence' / f"{PERSON['id']}.json", {'statements': []})
                client = Mock(model='test'); client.page.return_value = PAGE
                getattr(client, 'page' if stage == 'source_fetch' else 'extract').side_effect = ValueError('invalid')
                result = research.seed_one(root, PERSON, [{'url': PAGE['url']}], client)
                self.assertEqual(result['sources'][PAGE['url']]['error_stage'], stage)

    def test_seed_changed_text_restarts_partial_source(self):
        import federal_research as research
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); directory = root / 'data/raw/federal_research' / PERSON['id']
            federal.write(root / 'evidence' / f"{PERSON['id']}.json", {'statements': []})
            federal.write(directory / 'seeds.json', {'sources': {PAGE['url']: {
                'status': 'needs_retry', 'next_chunk': 3, 'source_text_sha256': 'old'}}, 'added_sids': []})
            client = Mock(model='test'); client.page.return_value = PAGE; client.extract.return_value = [ROW]
            result = research.seed_one(root, PERSON, [{'url': PAGE['url']}], client)
            client.extract.assert_called_once()
            self.assertEqual(result['added_sids'], ['s1'])

    def test_unavailable_source_remains_pending_for_cached_retry(self):
        import federal_research as research
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); directory = root / 'data/raw/federal_research' / PERSON['id']
            federal.write(root / 'evidence' / f"{PERSON['id']}.json", {'statements': []})
            (root / 'config').mkdir(); (root / 'config/federal_research_prompt.md').write_text('Research')
            raw = {'choices': [{'message': {'content': __import__('json').dumps({'statements': [{**ROW, 'url': PAGE['url']}], 'gaps': []})}}], 'usage': {'server_tool_use_details': {'web_search_requests': 1}}}
            federal.write(directory / 'pass-1.json', raw)
            client = Mock(model='test'); client.page.side_effect = RuntimeError('unavailable')
            first = research.research_one(root, PERSON, [], client, {}, 1, threading.Lock(), {})
            self.assertEqual(first['status'], 'needs_retry')
            client.page.side_effect = None; client.page.return_value = PAGE
            second = research.research_one(root, PERSON, [], client, {}, 1, threading.Lock(), {})
            self.assertEqual(second['status'], 'completed')
            self.assertEqual(second['added_sids'], ['s1']); client.chat.assert_not_called()

    def test_non_government_context_stays_out_of_public_evidence(self):
        page = {**PAGE, 'url': 'https://news.example/article'}
        statement = federal.validate_rows(page, [ROW], [PERSON], '2026-11-08')[0][0][1]
        public = federal.public_statement(statement)
        self.assertNotIn(QUOTE, public['context'])
        self.assertEqual(public['text'], QUOTE)
        self.assertTrue(public['attribution_span_sha256'])
        self.assertEqual(federal.public_statement(public), public)

    def test_malformed_research_formats_saved_retrieval_without_another_search(self):
        import federal_research as research
        import json
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); directory = root / 'data/raw/federal_research' / PERSON['id']
            federal.write(root / 'evidence' / f"{PERSON['id']}.json", {'statements': []})
            (root / 'config').mkdir(); (root / 'config/federal_research_prompt.md').write_text('Research')
            raw = {'choices': [{'message': {'content': 'Malformed provider output', 'annotations': [
                {'url_citation': {'url': PAGE['url'], 'content': PAGE['text']}}]}}], 'usage': {'server_tool_use_details': {'web_search_requests': 1}}}
            federal.write(directory / 'pass-1.json', raw)
            client = Mock(model='test'); client.page.return_value = PAGE
            client.chat.return_value = {'choices': [{'message': {'content': json.dumps({'statements': [{**ROW, 'url': PAGE['url']}], 'gaps': []})}}]}
            for _ in range(2):
                entry = research.research_one(root, PERSON, [], client, {'max_output_tokens': 8000}, 1, threading.Lock(), {})
                self.assertEqual(entry['status'], 'completed')
            client.chat.assert_called_once()
            self.assertEqual(len(client.chat.call_args.args), 3)  # No web tool supplied.




class DailyCoverageTests(unittest.TestCase):
    def snapshot(self, root, subjects):
        from datetime import datetime, timezone
        import federal_coverage
        with patch.object(federal_coverage, 'datetime', wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 11, 10, tzinfo=timezone.utc)
            result = federal_coverage.coverage(root, subjects, {})
        self.assertIn('daily', result)
        return result

    def test_named_query_uses_its_exact_checkpoint_and_page_queue_date(self):
        import hashlib
        import json
        from test_policy_subjects import INSTITUTION
        agency = {**INSTITUTION, 'id': 'new_agency', 'name': 'New Agency', 'organization_id': 'new_agency'}
        unrouted = {**agency, 'id': 'unrouted', 'name': 'Unrouted Agency', 'organization_id': 'unrouted'}
        groups = [
            {'id': 'commerce', 'organization_ids': ['commerce'], 'domains': ['commerce.gov'], 'queries': ['Commerce AI']},
            {'id': 'new', 'organization_ids': ['new_agency'], 'domains': ['agency.gov'], 'queries': ['Agency AI']},
        ]
        commerce_query = '("Official A" OR "Commerce") AI artificial intelligence superintelligence policy statements'
        agency_query = '("New Agency") AI artificial intelligence superintelligence policy statements'
        def query_key(group, query, domains):
            return hashlib.sha256(json.dumps([group, query, domains], sort_keys=True).encode()).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            federal.write(root / 'config/federal_sources.json', {'named_searches': True, 'groups': groups})
            federal.write(root / 'data/federal_state.json', {
                'groups': {'new': {'since': '2026-11-10'}},
                'queries': {
                    query_key('commerce', commerce_query, ['commerce.gov']): {'group': 'commerce', 'since': '2026-11-07'},
                    query_key('commerce', 'Commerce AI', ['commerce.gov']): {'group': 'commerce', 'since': '2026-11-10'},
                    query_key('new', agency_query, ['previous-agency.gov']): {'group': 'new', 'since': '2026-11-10'},
                },
                'pending': {
                    'https://commerce.gov/dated': {'group': 'commerce', 'queued_on': '2026-11-08', 'publishedDate': '2025-01-01'},
                    'https://commerce.gov/legacy': {'group': 'commerce', 'publishedDate': '2024-01-01'},
                    'https://agency.gov/new': {'group': 'new', 'queued_on': '2026-11-09'},
                },
            })
            result = self.snapshot(root, [PERSON, INSTITUTION, agency, unrouted])
            official = result['profiles'][PERSON['id']]['daily']['web']
            self.assertEqual(official, {
                'group': 'commerce', 'named_query': commerce_query, 'last_success_on': '2026-11-07',
                'age_days': 3, 'pending_named_queries': 1, 'group_pending_pages': 2,
            })
            self.assertEqual(result['profiles'][INSTITUTION['id']]['daily']['web'], official)
            new = result['profiles']['new_agency']['daily']['web']
            self.assertEqual(new['named_query'], agency_query)
            self.assertIsNone(new['last_success_on'])
            self.assertIsNone(new['age_days'])
            self.assertEqual(new['pending_named_queries'], 1)
            self.assertEqual(new['group_pending_pages'], 1)
            self.assertTrue(all(value is None for value in result['profiles']['unrouted']['daily']['web'].values()))
            web = result['daily']['web']
            self.assertEqual(web['pending_named_queries'], 2)
            self.assertEqual(web['last_success_on'], '2026-11-10')
            self.assertEqual(web['last_named_success_on'], '2026-11-07')
            self.assertEqual(web['pending_pages'], 3)
            self.assertEqual(web['pending_pages_without_queue_date'], 1)
            self.assertEqual(web['oldest_known_pending_on'], '2026-11-08')
            self.assertEqual(web['oldest_known_pending_age_days'], 2)

    def test_daily_x_cutoff_only_uses_current_completed_daily_jobs(self):
        from federal_x_config import fingerprint
        account = {'id': 'current', 'subject_id': PERSON['id'], 'handle': 'OfficialA',
                   'valid_from': '2023-01-01', 'valid_until': None}
        config = {'enabled': True, 'provider': 'x_api', 'since': '2023-01-01', 'historical_window': 'account',
                  'historical_until': '2026-11-08', 'accounts': [account]}
        base = {'account_id': account['id'], 'fingerprint': fingerprint(account), 'status': 'searched',
                'mode': 'daily', 'start': '2026-11-07', 'end': '2026-11-11'}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            federal.write(root / 'config/federal_x.json', config)
            federal.write(root / 'data/federal_x_api_state.json', {'jobs': {
                'success': {**base, 'query_end_time': '2026-11-10T18:00:00Z'},
                'nominal_only': {**base, 'end': '2026-11-12'},
                'pending': {**base, 'status': 'pending', 'query_end_time': '2026-11-10T20:00:00Z'},
                'stale': {**base, 'fingerprint': 'old', 'query_end_time': '2026-11-10T22:00:00Z'},
                'cohort': {**base, 'mode': 'historical', 'window': 'account', 'start': '2023-01-01',
                           'end': '2026-11-10', 'historical_until': '2026-11-10'},
            }})
            federal.write(root / 'data/federal_x_state.json', {'jobs': {
                'other_provider': {**base, 'query_end_time': '2026-11-10T23:00:00Z'},
            }})
            result = self.snapshot(root, [PERSON])
            profile = result['profiles'][PERSON['id']]
            self.assertEqual(profile['x_windows_searched'], 3)  # includes explicit cohort cutoff
            self.assertEqual(profile['daily']['x'], {
                'last_successful_cutoff': '2026-11-10T18:00:00Z', 'pending_windows': 1,
                'accounts_due_for_daily_check': 0,
            })
            self.assertEqual(result['daily']['x'], profile['daily']['x'])

    def test_daily_x_due_accounts_include_new_and_stale_mappings_without_counting_retired_accounts(self):
        from federal_x_config import fingerprint
        states = ['new', 'done', 'retired', 'stale', 'queued']
        subjects = [{**PERSON, 'id': state} for state in states]
        accounts = {state: {'id': state, 'subject_id': state, 'handle': state, 'valid_from': '2023-01-01',
                            'valid_until': '2026-11-10' if state == 'retired' else None} for state in states}
        config = {'enabled': True, 'provider': 'x_api', 'accounts': list(accounts.values())}
        def job(state, **changes):
            return {'account_id': state, 'fingerprint': fingerprint(accounts[state]), 'mode': 'daily',
                    'status': 'searched', 'start': '2026-11-07', 'end': '2026-11-11',
                    'query_end_time': '2026-11-10T18:00:00Z', **changes}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            federal.write(root / 'config/federal_x.json', config)
            new = self.snapshot(root, subjects[:1])['profiles']['new']['daily']['x']
            self.assertEqual(new.get('accounts_due_for_daily_check'), 1)
            self.assertIsNone(new['pending_windows'])
            self.assertIsNone(new['last_successful_cutoff'])
            federal.write(root / 'data/federal_x_api_state.json', {'jobs': {
                'done': job('done'),
                'retired': job('retired', end='2026-11-10', query_end_time='2026-11-09T18:00:00Z'),
                'stale': job('stale', fingerprint='old'),
                'queued': job('queued', status='pending'),
            }})
            result = self.snapshot(root, subjects)
            daily = {pid: row['daily']['x'] for pid,row in result['profiles'].items()}
            self.assertEqual({pid: row['accounts_due_for_daily_check'] for pid,row in daily.items()},
                             {'new':1, 'done':0, 'retired':0, 'stale':1, 'queued':1})
            self.assertIsNone(daily['stale']['last_successful_cutoff'])
            self.assertEqual(result['daily']['x']['accounts_due_for_daily_check'], 3)
            self.assertEqual(result['daily']['x']['pending_windows'], 1)

    def test_missing_checkpoint_files_keep_freshness_and_queue_age_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.snapshot(Path(tmp), [PERSON])
            profile = result['profiles'][PERSON['id']]['daily']
            self.assertTrue(all(value is None for value in profile['web'].values()))
            self.assertTrue(all(value is None for value in profile['x'].values()))
            self.assertIsNone(result['daily']['web']['pending_pages'])
            self.assertIsNone(result['daily']['web']['oldest_known_pending_age_days'])

    def test_first_queue_date_survives_retries_and_leaves_legacy_pages_unknown(self):
        import federal_sources
        from test_federal_daily import CONFIG, FederalTests
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            FederalTests().fixture(root)
            legacy = {**PAGE, 'url': PAGE['url'] + '-legacy'}
            state_path = root / 'data/federal_state.json'
            federal.write(state_path, {'groups': {}, 'queries': {}, 'processed': {}, 'pending': {
                legacy['url']: {'url': legacy['url'], 'group': 'commerce'},
            }})
            client = Mock()
            client.search.return_value = [legacy, PAGE]
            client.page.side_effect = RuntimeError('temporary failure')
            with patch.object(federal_sources, 'Client', return_value=client), patch.object(federal, 'today', side_effect=['2026-11-08', '2026-11-10']):
                federal.collect(root, CONFIG)
                federal.collect(root, CONFIG)
            queue = federal.read(state_path, {})['pending']
            self.assertEqual(queue[PAGE['url']].get('queued_on'), '2026-11-08')
            self.assertNotIn('queued_on', queue[legacy['url']])


if __name__ == '__main__':
    unittest.main()
