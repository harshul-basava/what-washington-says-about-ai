import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import federal_archives as archive


class GovinfoTurnTests(unittest.TestCase):
    def setUp(self):
        self.url = 'https://www.govinfo.gov/content/pkg/CHRG-119shrg63889/html/CHRG-119shrg63889.htm'
        self.quote = 'Artificial intelligence must help workers and protect their privacy.'
        self.other = 'Artificial intelligence needs a complete ban across the country.'
        self.raw = ('September 17, 2025\nWitness: Ethan A. Klein\n'
                    '    Mr. Klein. ' + self.quote + '\n'
                    '    Senator Van Hollen. ' + self.other + '\n'
                    'I spoke to Mr. Klein. Another sentence must not become his words.\n')
        self.subject = {'id': 'klein', 'name': 'Ethan A. Klein', 'aliases': [], 'roles': [],
                        'entity_type': 'person', 'organization_id': 'ostp',
                        'source_speaker_aliases': [{'label': 'Mr. Klein.', 'source_urls': [self.url],
                          'source_url': self.url, 'valid_from': '2025-09-17',
                          'valid_until': '2025-09-18', 'verified_on': '2026-11-12'}]}

    def page(self, raw=None, url=None):
        return archive.page_from_bytes(url or self.url, ('<html><pre>' + (raw or self.raw) + '</pre></html>').encode())

    def validate(self, quote=None, page=None, subject=None):
        row = {'subject_id': 'klein', 'quote': quote or self.quote,
               'attribution_quote': 'Witness: Ethan A. Klein', 'kind': 'personal',
               'date': '2025-09-17', 'date_quote': 'September 17, 2025'}
        return archive.federal.validate_rows(page or self.page(), [row], [subject or self.subject], '2026-11-12')

    def test_reviewed_mixed_case_label_accepts_only_its_line_bound_turn(self):
        rows, rejected = self.validate()
        self.assertEqual(rejected, 0)
        self.assertEqual(rows[0][1]['context'], 'Mr. Klein. ' + self.quote)
        self.assertEqual(self.validate(self.other), ([], 1))
        self.assertEqual(self.validate(self.quote + ' Senator Van Hollen. ' + self.other), ([], 1))

    def test_reviewed_lieutenant_general_label_requires_exact_source_and_paragraph(self):
        subject=copy.deepcopy(self.subject)
        subject['source_speaker_aliases'][0]['label']='Lt. General Klein.'
        raw=self.raw.replace('Mr. Klein.', 'Lt. General Klein.')
        rows,rejected=self.validate(page=self.page(raw),subject=subject)
        self.assertEqual(rejected,0)
        self.assertEqual(rows[0][1]['attribution']['speaker_label'],'Lt. General Klein.')
        self.assertEqual(self.validate(self.other,self.page(raw),subject),([],1))
        for invalid in [raw.replace('    Lt. General Klein.','Lt. General Klein.'),
                        raw.replace('    Lt. General Klein.','    Lt. General Jones.')]:
            self.assertEqual(self.validate(page=self.page(invalid),subject=subject),([],1))

    def test_inline_name_and_written_question_do_not_extend_a_speaker_turn(self):
        raw = ('September 17, 2025\nWitness: Ethan A. Klein\n'
               '    Senator Van Hollen. I spoke to Mr. Klein. ' + self.quote + '\n')
        self.assertEqual(self.validate(page=self.page(raw)), ([], 1))
        for boundary in ['    Question 1. ', '    Answer. ', '    [Additional material follows.]\n',
                         '    Prepared Statement of Another Witness\n', '     ARTIFICIAL INTELLIGENCE\n']:
            raw = self.raw.split('    Senator')[0] + boundary + self.other + '\n'
            self.assertEqual(self.validate(self.other, self.page(raw)), ([], 1))

    def test_unsupported_speakers_still_end_the_previous_turn(self):
        for label in ['    Director Burns. ', '    The Clerk. ', '    Mr. Scott of Virginia. ',
                      '    Senator Van Hollen.\n', 'Senator Van Hollen. ',
                      '        Director Burns. ', '    UNKNOWN SPEAKER: ']:
            with self.subTest(label=label):
                raw = self.raw.replace('    Senator Van Hollen. ', label)
                self.assertEqual(self.validate(self.other, self.page(raw)), ([], 1))

    def test_written_answers_do_not_inherit_the_oral_hearing_date(self):
        for heading in ['    [Prepared questions submitted to Mr. Klein follow:]\n',
                        '    [Questions for the record with answers supplied follow:]\n',
                        '      Response to Written Questions Submitted to Mr. Klein\n']:
            raw = self.raw + heading + '    Mr. Klein. ' + self.other + '\n'
            self.assertEqual(self.validate(self.other, self.page(raw)), ([], 1))

    def test_line_proof_is_required_and_cannot_transfer_to_another_source_or_person(self):
        page = self.page()
        page.pop('transcript_lines', None)
        self.assertEqual(self.validate(page=page), ([], 1))
        self.assertEqual(self.validate(page=self.page(url='https://example.gov/hearing')), ([], 1))
        other = copy.deepcopy(self.subject); other['source_speaker_aliases'] = []
        self.assertEqual(self.validate(subject=other), ([], 1))

    def test_daily_fetch_preserves_the_same_line_bound_proof(self):
        import httpx
        client = archive.sources.Client.__new__(archive.sources.Client)
        response = httpx.Response(200, text='<pre>' + self.raw + '</pre>', request=httpx.Request('GET', self.url))
        with patch.object(archive.sources.httpx, 'get', return_value=response):
            page = client.page({'url': self.url}, ['govinfo.gov'])
        self.assertEqual(self.validate(page=page)[1], 0)

    def test_daily_rechecks_changed_line_boundaries_with_unchanged_normalized_text(self):
        pages = [self.page(), self.page(self.raw.replace('    Mr. Klein.', 'Mr. Klein.'))]
        self.assertEqual(pages[0]['text'], pages[1]['text'])
        calls = []
        class Client:
            def __init__(self, *args): pass
            def page(self, *args): return pages[len(calls)]
            def extract(self, *args): calls.append(1); return []
        config = {'bootstrap_days': 14, 'overlap_days': 3, 'pages_per_group': 1, 'collection_max_cost': 1,
                  'groups': [{'id': 'ostp', 'queries': [], 'domains': ['govinfo.gov'], 'watch_urls': [self.url]}]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive.federal.write(root/'evidence/klein.json', {'statements': []})
            with patch.object(archive.federal.policy_subjects, 'load_subjects', return_value=[{**self.subject, 'branch': 'executive'}]), \
                 patch.object(archive.federal.sources, 'Client', Client):
                archive.federal.collect(root, config)
                archive.federal.collect(root, config)
        self.assertEqual(len(calls), 2)


if __name__ == '__main__':
    unittest.main()
