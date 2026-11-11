import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/daily'))
import federal


class TranscriptSpeakerTests(unittest.TestCase):
    def setUp(self):
        self.url = 'https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20250618.pdf'
        self.identity = 'https://www.federalreserve.gov/aboutthefed/bios/board/powell.htm'
        self.subject = {
            'id': 'powell', 'name': 'Jerome H. Powell', 'aliases': ['Jerome Powell'],
            'entity_type': 'person', 'organization_id': 'federal_reserve', 'roles': [],
            'source_speaker_aliases': [{'label': 'CHAIR POWELL.', 'source_urls': [self.url],
                                       'source_url': self.identity, 'verified_on': '2026-11-11',
                                       'valid_from': '2018-02-05', 'valid_until': '2026-05-23'}]}
        self.quote = 'AI should be creating jobs at the same time.'
        self.reporter = 'Will AI replace many workers across the economy this year?'
        self.header = 'Transcript of Chair Powell’s Press Conference June 18, 2025'
        self.page = {'url': self.url, 'verified_via': 'exact_normalized_page_text',
                     'text': self.header + ' CHAIR POWELL. So this is the question. ' + self.quote +
                             ' JANE DOE. ' + self.reporter + ' CHAIR POWELL. We do not know yet.'}
        self.row = {'subject_id': 'powell', 'quote': self.quote, 'attribution_quote': self.header,
                    'kind': 'personal', 'date': '2025-06-18', 'date_quote': 'June 18, 2025'}

    def validate(self, row=None, page=None, subject=None):
        return federal.validate_rows(page or self.page, [row or self.row],
                                     [subject or self.subject], '2026-11-11')

    def test_reviewed_speaker_turn_recovers_header_and_document_author_rows(self):
        for basis in ('local_span', 'document_author'):
            with self.subTest(basis=basis):
                accepted, rejected = self.validate({**self.row, 'attribution_basis': basis})
                self.assertEqual(rejected, 0)
                statement = accepted[0][1]
                self.assertEqual(statement['context'], 'CHAIR POWELL. So this is the question. ' + self.quote)
                self.assertEqual(statement['attribution']['basis'], 'local_span')
                self.assertEqual(statement['attribution']['speaker_label'], 'CHAIR POWELL.')
                self.assertEqual(statement['attribution']['speaker_identity_source_url'], self.identity)

    def test_reporter_quote_is_rejected_even_with_a_named_document_header(self):
        header = 'Remarks by Jerome Powell. ' + self.header
        page = {**self.page, 'text': header + self.page['text'][len(self.header):]}
        row = {**self.row, 'quote': self.reporter, 'attribution_quote': header,
               'attribution_basis': 'document_author'}
        self.assertEqual(self.validate(row, page), ([], 1))

    def test_quote_cannot_cross_the_next_speaker_boundary(self):
        quote = self.quote + ' JANE DOE. ' + self.reporter
        row = {**self.row, 'quote': quote, 'attribution_quote': self.page['text']}
        self.assertEqual(self.validate(row), ([], 1))

    def test_reporter_initials_also_end_the_reviewed_speaker_turn(self):
        page = {**self.page, 'text': self.page['text'].replace('JANE DOE.', 'J. DOE.')}
        self.assertEqual(self.validate({**self.row, 'quote': self.reporter}, page), ([], 1))

    def test_full_name_matching_does_not_gain_an_automatic_surname_alias(self):
        subject = {**self.subject, 'source_speaker_aliases': []}
        self.assertEqual(self.validate(subject=subject), ([], 1))
        subject = {**self.subject, 'name': 'Other Powell', 'aliases': [], 'source_speaker_aliases': []}
        self.assertEqual(self.validate(subject=subject), ([], 1))

    def test_daily_candidate_selection_uses_reviewed_source_identity(self):
        text = 'CHAIR POWELL. ' + self.quote
        self.assertFalse(federal.contains_name(text, self.subject))
        self.assertTrue(federal.contains_name(text, self.subject, source_url=self.url))
        self.assertFalse(federal.contains_name(text, self.subject, source_url='https://news.example/transcript'))
        self.assertFalse(federal.contains_name('Only a question by JANE DOE.', self.subject, source_url=self.url))

    def test_daily_collection_accepts_the_reviewed_speaker_without_a_full_name_in_the_pdf(self):
        page = self.page
        row = self.row

        class Client:
            def __init__(self, *args):
                pass

            def page(self, *args):
                return page

            def extract(self, *args):
                return [row]

        config = {'bootstrap_days': 14, 'overlap_days': 3, 'pages_per_group': 1, 'collection_max_cost': 1,
                  'groups': [{'id': 'fed', 'queries': [], 'domains': ['federalreserve.gov'], 'watch_urls': [self.url]}]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / 'evidence/powell.json'
            evidence.parent.mkdir()
            evidence.write_text(json.dumps({'statements': []}))
            subject = {**self.subject, 'branch': 'executive'}
            with patch.object(federal.policy_subjects, 'load_subjects', return_value=[subject]), patch.object(federal.sources, 'Client', Client):
                result = federal.collect(root, config)
            self.assertEqual(result['added'], {'powell': ['s1']})
            self.assertEqual(json.loads(evidence.read_text())['statements'][0]['text'], self.quote)

    def test_reviewed_alias_applies_only_to_the_exact_official_source(self):
        for url in ('https://news.example/FOMCpresconf20250618.pdf',
                    'https://www.federalreserve.gov/other/transcript.pdf',
                    self.url + '?unreviewed=1'):
            with self.subTest(url=url):
                self.assertEqual(self.validate(page={**self.page, 'url': url}), ([], 1))

    def test_historical_speaker_identity_requires_a_verified_day_within_its_interval(self):
        for day, anchor in [('2026-05-23', 'May 23, 2026'), (None, None)]:
            with self.subTest(day=day):
                page = {**self.page, 'text': (anchor or '') + ' ' + self.page['text']}
                row = {**self.row, 'date': day, 'date_quote': anchor}
                self.assertEqual(self.validate(row, page), ([], 1))

    def test_missing_identity_evidence_cannot_enable_a_speaker_alias(self):
        subject = copy.deepcopy(self.subject)
        del subject['source_speaker_aliases'][0]['source_url']
        self.assertEqual(self.validate(subject=subject), ([], 1))

    def test_reviewed_author_title_alias_matches_a_full_named_speech_header(self):
        subject = {'name': 'John K. Hurley', 'aliases': ['John Hurley'], 'roles': [{
            'title': 'Undersecretary of the Treasury for Terrorism and Financial Intelligence (TFI)'}],
            'author_title_aliases': ['Under Secretary for Terrorism and Financial Intelligence']}
        header = ('Remarks by Under Secretary for Terrorism and Financial Intelligence John K. Hurley '
                  'at the Association of Certified Anti-Money Laundering Specialists Assembly Conference')
        self.assertTrue(federal.explicit_document_author(header, subject))
        unreviewed = {**subject, 'author_title_aliases': []}
        self.assertFalse(federal.explicit_document_author(header, unreviewed))
        other = header.replace('John K. Hurley', 'Someone Else') + ', with John K. Hurley'
        self.assertFalse(federal.explicit_document_author(other, subject))

    def test_full_name_possessive_remarks_header_identifies_the_document_author(self):
        subject = {'name': 'Mark Paoletta', 'roles': [], 'author_title_aliases': ['Deputy Director']}
        header = 'Deputy Director Mark Paoletta’s Remarks to the Financial Literacy and Education Commission'
        self.assertTrue(federal.explicit_document_author(header, subject))
        self.assertFalse(federal.explicit_document_author(header.replace('Mark Paoletta', 'Someone Else') + ', thanking Mark Paoletta', subject))
        self.assertFalse(federal.explicit_document_author('Mark Paoletta’s Press Conference Transcript', subject))
        self.assertFalse(federal.explicit_document_author(header + ': Questions and Answers', subject))

    def test_daily_validation_recovers_an_omitted_basis_only_for_an_exact_author_header(self):
        subject = {**self.subject, 'name': 'Mark Paoletta', 'aliases': [], 'source_speaker_aliases': [],
                   'author_title_aliases': ['Deputy Director']}
        header = 'Deputy Director Mark Paoletta’s Remarks to the Financial Literacy and Education Commission'
        page = {**self.page, 'url': 'https://www.consumerfinance.gov/speech',
                'text': header + ' June 18, 2025. ' + 'Introduction. ' * 400 + self.quote}
        row = {**self.row, 'attribution_quote': header}
        accepted, rejected = self.validate(row, page, subject)
        self.assertEqual(rejected, 0)
        self.assertEqual(accepted[0][1]['attribution']['basis'], 'document_author')
        self.assertEqual(self.validate({**row, 'attribution_basis': 'local_span'}, page, subject), ([], 1))
        self.assertEqual(self.validate(row, {**page, 'text': 'Preface. ' * 800 + page['text']}, subject), ([], 1))
        self.assertEqual(self.validate(row, {**page, 'url': 'https://news.example/speech'}, subject), ([], 1))

    def test_named_message_header_attributes_distant_official_letter_text(self):
        subject = {**self.subject, 'name': 'Jared Isaacman', 'aliases': [],
                   'source_speaker_aliases': [], 'organization_id': 'nasa',
                   'roles': [{'title': 'Administrator'}]}
        header = 'A Message From Administrator Jared Isaacman'
        page = {**self.page, 'url': 'https://www.nasa.gov/letter',
                'text': header + ' June 18, 2025. ' + 'Introduction. ' * 800 + self.quote}
        row = {**self.row, 'attribution_quote': header, 'attribution_basis': 'document_author'}
        accepted, rejected = self.validate(row, page, subject)
        self.assertEqual(rejected, 0)
        self.assertEqual(accepted[0][1]['attribution']['basis'], 'document_author')
        self.assertTrue(federal.explicit_document_author(header + ' - NASA', subject))
        for other in (header.replace('From', 'To'),
                      header.replace('Jared Isaacman', 'Someone Else') + ', thanking Jared Isaacman',
                      header + "'s Chief of Staff", header + ' Office',
                      header + ': Questions and Answers',
                      'A report about ' + header,
                      'Advance Policy Questions for Administrator Jared Isaacman'):
            with self.subTest(header=other):
                self.assertFalse(federal.explicit_document_author(other, subject))
        self.assertEqual(self.validate(row, {**page, 'url': 'https://news.example/letter'}, subject), ([], 1))
        self.assertEqual(self.validate(row, {**page, 'text': 'Preface. ' * 800 + page['text']}, subject), ([], 1))


if __name__ == '__main__':
    unittest.main()
