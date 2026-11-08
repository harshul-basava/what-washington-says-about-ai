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
        def chat(*args, **kwargs):
            started.set(); release.wait(5); return {}
        class BudgetError(Exception): pass
        client.llm = SimpleNamespace(spent=lambda _: 0, spent_this_month=lambda _: 999,
            BUDGETS={'openrouter': 10, 'monthly': {'openrouter': 1}}, BudgetExceeded=BudgetError, chat=chat)
        client.metadata = {'pricing': {'prompt': '.001', 'completion': '.001'}}
        client.baseline = 0; client.max_cost = .3; client.daily = False; client.model = 'test'
        client.lock = threading.Lock(); client.reserved = 0
        thread = threading.Thread(target=client.chat, args=([{'role': 'user', 'content': 'a'}], 'test', 10))
        thread.start(); self.assertTrue(started.wait(2))
        try:
            with self.assertRaises(BudgetError):
                client.chat([{'role': 'user', 'content': 'a'}], 'test', 10)
        finally:
            release.set(); thread.join()
        self.assertAlmostEqual(client.reserved, 0)

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


if __name__ == '__main__':
    unittest.main()
