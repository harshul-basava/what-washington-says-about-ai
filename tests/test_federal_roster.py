import copy
import json
import tempfile
import unittest
from pathlib import Path

import federal_roster as roster


class FederalRosterTests(unittest.TestCase):
    def fixture(self, root):
        def write(path, value):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value))
        self.write = write
        write(root / 'data/roster.json', [])
        write(root / 'config/policy_subjects.json', {'version': 1, 'coverage_mode': 'current_government',
            'organizations': [{'id': 'dept', 'name': 'Department'}, {'id': 'office', 'name': 'Office', 'parent_id': 'dept'}],
            'subjects': [{'id': 'exec_person', 'name': 'Current Person', 'entity_type': 'person', 'branch': 'executive',
                          'organization_id': 'dept', 'roles': []}]})
        write(root / 'config/federal_scope.json', {'version': 1, 'mode': 'current_government', 'reviewed_on': '2026-11-10',
            'profiles': [{'subject_id': 'exec_person', 'decision': 'include', 'reason': 'Current official',
                          'source_url': 'https://example.gov/leadership', 'checked_on': '2026-11-10'}]})
        self.inventory = {'version': 1, 'checked_on': '2026-11-10', 'organizations': [
            {'id': 'dept', 'registry_id': 'dept', 'name': 'Department', 'parent_id': None, 'status': 'reviewed',
             'directory_urls': ['https://example.gov/leadership'], 'reviewed_urls': ['https://example.gov/leadership'],
             'checked_on': '2026-11-10', 'notes': 'Leadership reviewed.'},
            {'id': 'office', 'registry_id': 'office', 'name': 'Office', 'parent_id': 'dept', 'status': 'pending',
             'directory_urls': ['https://example.gov/office'], 'reviewed_urls': [], 'checked_on': '2026-11-10',
             'notes': 'Directory not yet reviewed.'}], 'roles': [
            {'id': 'dept_head', 'organization_id': 'dept', 'title': 'Secretary', 'status': 'included',
             'subject_id': 'exec_person', 'candidate_name': 'Current Person', 'authority_class': 'senior_leadership',
             'authority_reason': 'Leads the department.', 'source_urls': ['https://example.gov/leadership'],
             'checked_on': '2026-11-10', 'current_service_evidence': 'Current Person is Secretary.'}]}
        write(root / roster.INVENTORY, self.inventory)

    def test_missing_inventory_is_unavailable_not_zero_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(roster.coverage_report(Path(tmp))['status'], 'unavailable')

    def test_included_requires_current_person_and_does_not_enable_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            self.inventory['roles'][0]['subject_id'] = 'unknown'
            self.write(root / roster.INVENTORY, self.inventory)
            with self.assertRaisesRegex(ValueError, 'eligible'):
                roster.load_inventory(root)
            self.inventory['roles'][0]['status'] = 'candidate'
            self.write(root / roster.INVENTORY, self.inventory)
            report = roster.coverage_report(root)
            self.assertEqual(report['summary']['included_people'], 0)
            self.assertEqual(report['summary']['candidate_roles'], 1)

    def test_dual_roles_count_person_once_and_pending_child_blocks_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            second = {**self.inventory['roles'][0], 'id': 'office_head', 'organization_id': 'office'}
            self.inventory['roles'].append(second)
            self.write(root / roster.INVENTORY, self.inventory)
            report = roster.coverage_report(root)
            self.assertEqual(report['summary']['included_people'], 1)
            dept = next(o for o in report['organizations'] if o['id'] == 'dept')
            self.assertEqual(dept['included_people'], 1)
            self.assertEqual(dept['included_roles'], 2)
            self.assertFalse(dept['discovery_complete'])
            self.inventory['organizations'][1].update(status='reviewed', reviewed_urls=['https://example.gov/office'])
            self.inventory['organizations'][0]['name'] = 'Renamed Department'
            self.write(root / roster.INVENTORY, self.inventory)
            dept = next(o for o in roster.coverage_report(root)['organizations'] if o['id'] == 'dept')
            self.assertTrue(dept['discovery_complete'])
            self.assertEqual(dept['id'], 'dept')

    def test_vacancy_requires_positive_evidence_not_failed_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            self.inventory['roles'][0].update(status='vacant', subject_id=None, current_service_evidence='')
            self.write(root / roster.INVENTORY, self.inventory)
            with self.assertRaisesRegex(ValueError, 'evidence'):
                roster.load_inventory(root)

    def test_verified_roles_outside_selected_roster_are_not_unresolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            self.inventory['roles'].append({**self.inventory['roles'][0], 'id': 'outside_selection',
                'status': 'not_selected', 'subject_id': None, 'candidate_name': 'Another Official'})
            self.write(root / roster.INVENTORY, self.inventory)
            report = roster.coverage_report(root)
            self.assertEqual(report['summary']['included_people'], 1)
            self.assertEqual(report['summary']['not_selected_roles'], 1)
            self.assertEqual(report['summary']['unresolved_roles'], 0)
            self.assertEqual(report['summary']['candidate_roles'], 0)

    def test_directory_change_and_failure_preserve_scope_and_last_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            before = (root / 'config/federal_scope.json').read_bytes()
            one = roster.check_directories(root, asof='2026-11-10', fetch=lambda _: 'Current Person is Secretary.')
            self.assertEqual(one['checked'], 2)
            self.assertEqual(roster.check_directories(root, asof='2026-11-11', fetch=lambda _: 'unused')['checked'], 0)
            two = roster.check_directories(root, asof='2026-11-17', fetch=lambda _: 'Different Person is Secretary.')
            self.assertEqual(two['review_needed'], 2)
            def failed(_): raise OSError('403')
            roster.check_directories(root, asof='2026-11-24', fetch=failed)
            state = json.loads((root / roster.CHECKS).read_text())
            row = state['sources']['https://example.gov/leadership']
            self.assertEqual(row['status'], 'unavailable')
            self.assertEqual(row['last_success'], '2026-11-17')
            self.assertTrue(row['needs_review'])
            self.assertEqual((root / 'config/federal_scope.json').read_bytes(), before)

    def test_small_directory_batches_visit_oldest_sources_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            seen = []
            for _ in range(2):
                roster.check_directories(root, asof='2026-11-10', max_pages=1,
                    fetch=lambda url: seen.append(url) or 'Leadership directory')
            self.assertEqual(len(set(seen)), 2)


if __name__ == '__main__': unittest.main()
