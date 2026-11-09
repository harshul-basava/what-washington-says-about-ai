import copy
import json
import tempfile
import unittest
from pathlib import Path

import policy_judgments as p
from test_policy_judgments import ITEM, REGISTRY


PERSON = {'id': 'executive_a', 'name': 'Official A', 'entity_type': 'person', 'branch': 'executive',
          'organization_id': 'commerce', 'roles': [
              {'organization_id': 'commerce', 'title': 'Secretary', 'start_date': '2025-02-01',
               'end_date': None, 'verified_on': '2026-11-07', 'source_url': 'https://example.gov/role'},
              {'organization_id': 'task_force', 'title': 'Member', 'start_date': None,
               'end_date': None, 'verified_on': '2026-11-07', 'source_url': 'https://example.gov/members'}]}
INSTITUTION = {'id': 'commerce', 'name': 'Commerce', 'entity_type': 'institution', 'branch': 'executive',
               'organization_id': 'commerce', 'source_url': 'https://example.gov', 'roles': []}
SUBJECTS = {'version': 1, 'verified_on': '2026-11-07',
            'organizations': [{'id': 'commerce', 'name': 'Commerce'}, {'id': 'task_force', 'name': 'Task force'}],
            'subjects': [PERSON, INSTITUTION]}
ATTRIBUTION = {'kind': 'official_role', 'speaker': 'Official A', 'role': 'Secretary',
               'organization_id': 'commerce', 'note': 'Named speaker in the department release.'}


class SubjectTests(unittest.TestCase):
    def fixture(self, root):
        p.write_json(root / 'config/policies.json', REGISTRY)
        (root / 'config/policy_rubric.md').write_text('rubric')
        p.write_json(root / 'config/policy_subjects.json', SUBJECTS)
        p.write_json(root / 'data/roster.json', [{'id': 'P', 'name': 'Person', 'party': 'Democrat',
            'state': 'CA', 'chamber': 'house', 'status': 'current'}])
        p.write_json(root / 'evidence/P.json', {'statements': [{**ITEM, 'verified': True}]})
        stmt = {**ITEM, 'verified': True, 'attribution': ATTRIBUTION}
        p.write_json(root / 'evidence/executive_a.json', {'statements': [stmt]})
        p.write_json(root / 'evidence/commerce.json', {'statements': []})

    def test_current_scope_removes_former_profiles_candidates_and_stale_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            p.build(root)
            original = (root / 'evidence/executive_a.json').read_bytes()
            p.write_json(root / 'config/federal_scope.json', {'version': 1, 'mode': 'current_government',
                'reviewed_on': '2026-11-09', 'profiles': [
                    {'subject_id': 'executive_a', 'decision': 'exclude', 'reason': 'Former official',
                     'checked_on': '2026-11-09', 'source_url': 'https://example.gov/former'},
                    {'subject_id': 'commerce', 'decision': 'include', 'reason': 'Active government institution',
                     'checked_on': '2026-11-09', 'source_url': 'https://example.gov/commerce'}]})
            result = p.build(root)
            self.assertEqual({m['id'] for m in result['members']}, {'P', 'commerce'})
            self.assertEqual({s['person_id'] for s in p.candidates(root, REGISTRY)}, {'P'})
            self.assertFalse((root / 'site/data/policy_members/executive_a.json').exists())
            self.assertEqual((root / 'evidence/executive_a.json').read_bytes(), original)
            self.assertEqual(result['federal_research']['summary']['people'], 0)

    def test_current_scope_excludes_unreviewed_profiles_and_requires_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            scope = {'version': 1, 'mode': 'current_government', 'reviewed_on': '2026-11-09',
                     'profiles': []}
            p.write_json(root / 'config/federal_scope.json', scope)
            self.assertEqual([m['id'] for m in p.build(root)['members']], ['P'])
            scope['profiles'] = [{'subject_id': 'executive_a', 'decision': 'include',
                                 'reason': 'Current', 'checked_on': '2026-11-09'}]
            p.write_json(root / 'config/federal_scope.json', scope)
            with self.assertRaisesRegex(ValueError, 'scope'):
                p.build(root)

    def test_required_current_scope_cannot_silently_fall_back_to_all_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            p.write_json(root / 'config/policy_subjects.json', {**SUBJECTS, 'coverage_mode': 'current_government'})
            with self.assertRaisesRegex(ValueError, 'scope'):
                p.build(root)

    def test_public_exports_exclude_copied_reporting_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            copied = 'A copied reporting paragraph that must remain in local verification storage.'
            statement = {**ITEM, 'verified': True, 'attribution': ATTRIBUTION, 'context': copied,
                         'url': 'https://news.example/article'}
            p.write_json(root / 'evidence/executive_a.json', {'statements': [statement]})
            p.build(root)
            exported = (root / 'site/data/policy_members/executive_a.json').read_text()
            self.assertNotIn(copied, exported)
            self.assertIn('attribution_span_sha256', exported)

    def test_offline_build_adds_unique_profiles_without_copying_official_quotes_to_institution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            result = p.build(root)
            subjects = {s['id']: s for s in result['members']}
            self.assertEqual(set(subjects), {'P', 'executive_a', 'commerce'})
            self.assertEqual(subjects['executive_a']['entity_type'], 'person')
            self.assertIsNone(subjects['executive_a']['party'])
            self.assertEqual(subjects['executive_a']['research']['statements'], 1)
            self.assertEqual(result['federal_research']['summary']['people'], 1)
            self.assertEqual(len(subjects['executive_a']['roles']), 2)
            self.assertEqual(subjects['commerce']['policies'][ITEM['targets'][0]]['candidates'], 0)
            self.assertEqual(subjects['P']['branch'], 'legislative')
            self.assertEqual(subjects['P']['source_count'], 1)
            detail = p.read_json(root / 'site/data/policy_members/executive_a.json')
            self.assertEqual(detail['policies'][ITEM['targets'][0]][0]['attribution'], ATTRIBUTION)
            self.assertEqual(len(detail['statements']), 1)
            self.assertEqual(result['organizations'][0]['name'], 'Commerce')

    def test_attribution_reaches_prompt_and_cache_without_changing_legacy_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            items = p.candidates(root, REGISTRY)
            self.assertEqual(next(s for s in items if s['person_id'] == 'P'), ITEM)
            new = next(s for s in items if s['person_id'] == 'executive_a')
            self.assertEqual(new['attribution'], ATTRIBUTION)
            prompt = p.messages([new], REGISTRY, 'rubric')
            self.assertIn('official_role', prompt[1]['content'])
            self.assertIn('institution', prompt[0]['content'])
            self.assertNotEqual(p.fingerprint([new], REGISTRY, 'rubric', 'model'),
                p.fingerprint([{**new, 'attribution': {**ATTRIBUTION, 'kind': 'personal'}}], REGISTRY, 'rubric', 'model'))

    def test_missing_attribution_and_duplicate_subjects_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            p.write_json(root / 'evidence/executive_a.json', {'statements': [{**ITEM, 'verified': True}]})
            with self.assertRaisesRegex(ValueError, 'attribution'):
                p.candidates(root, REGISTRY)
            duplicate = copy.deepcopy(SUBJECTS)
            duplicate['subjects'].append(PERSON)
            p.write_json(root / 'config/policy_subjects.json', duplicate)
            with self.assertRaisesRegex(ValueError, 'duplicate|Duplicate'):
                p.build(root)

    def test_bad_role_reference_and_reversed_dates_fail_closed(self):
        for change in ({'organization_id': 'missing'}, {'end_date': '2020-01-01'}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); self.fixture(root)
                invalid = copy.deepcopy(SUBJECTS)
                invalid['subjects'][0]['roles'][0].update(change)
                p.write_json(root / 'config/policy_subjects.json', invalid)
                with self.assertRaises(ValueError):
                    p.build(root)

    def test_organization_filters_include_parents_once_and_reject_cycles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            config = copy.deepcopy(SUBJECTS)
            config['organizations'].append({'id': 'government', 'name': 'Government'})
            config['organizations'][0]['parent_id'] = 'government'
            p.write_json(root / 'config/policy_subjects.json', config)
            member = next(s for s in p.build(root)['members'] if s['id'] == 'executive_a')
            self.assertEqual(set(member['organization_ids']), {'commerce', 'government', 'task_force'})
            config['organizations'][-1]['parent_id'] = 'commerce'
            p.write_json(root / 'config/policy_subjects.json', config)
            with self.assertRaises(ValueError):
                p.build(root)

    def test_no_policy_matches_still_exports_source_library_and_metadata_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            p.write_json(root / 'evidence/executive_a.json', {'statements': [
                {**ITEM, 'text': 'We support secure technology.', 'verified': True, 'attribution': ATTRIBUTION}]})
            first = p.build(root)
            detail = p.read_json(root / 'site/data/policy_members/executive_a.json')
            self.assertEqual(detail['policies'], {})
            self.assertEqual(detail['statements'][0]['text'], 'We support secure technology.')
            changed = copy.deepcopy(SUBJECTS)
            changed['subjects'][0]['description'] = 'Corrected profile description'
            p.write_json(root / 'config/policy_subjects.json', changed)
            self.assertNotEqual(first['chart_revision'], p.build(root)['chart_revision'])

    def test_attribution_names_the_profile_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            stmt = {**ITEM, 'verified': True, 'attribution': {**ATTRIBUTION, 'speaker': 'A different person'}}
            p.write_json(root / 'evidence/executive_a.json', {'statements': [stmt]})
            with self.assertRaisesRegex(ValueError, 'speaker'):
                p.candidates(root, REGISTRY)
