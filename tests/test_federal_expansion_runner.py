import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/federal_expansion_runner.py'


class ExpansionRunnerTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(), 'The resumable cohort runner must exist')
        spec = importlib.util.spec_from_file_location('expansion_runner', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_cohort_cannot_include_excluded_or_duplicate_profiles(self):
        manifest = {'cohorts': [{'id': 'expansion_01', 'subject_ids': ['a', 'b']}]}
        self.assertEqual(self.module.select_ids(manifest, 'expansion_01', {'a', 'b'}), ['a', 'b'])
        with self.assertRaises(ValueError):
            self.module.select_ids(manifest, 'expansion_01', {'a'})
        manifest['cohorts'][0]['subject_ids'] = ['a', 'a']
        with self.assertRaises(ValueError):
            self.module.select_ids(manifest, 'expansion_01', {'a'})

    def test_refresh_excludes_new_cohorts_and_retains_pilot(self):
        manifest = {'cohorts': [
            {'id': 'pilot', 'subject_ids': ['pilot']},
            {'id': 'expansion_01', 'subject_ids': ['new']}]}
        self.assertEqual(self.module.select_ids(manifest, 'existing_refresh', {'old', 'pilot', 'new'}), ['old', 'pilot'])

    def test_one_allowance_covers_every_stage(self):
        self.assertAlmostEqual(self.module.remaining_allowance(25, 100, 106), 19)
        self.assertEqual(self.module.remaining_allowance(25, 100, 126), 0)
        with self.assertRaises(ValueError):
            self.module.remaining_allowance(25, 100, 99)

    def test_original_seed_progress_survives_a_fresh_runner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'data').mkdir()
            original = {'sources': {'https://agency.gov/speech': {'status': 'completed', 'next_chunk': 2}}, 'added_sids': ['s1']}
            (root / 'data/federal_seed_research.json').write_text(json.dumps({'profiles': {'a': original}}))
            self.module.restore_seed_checkpoints(root, ['a'])
            path = root / 'data/raw/federal_research/a/seeds.json'
            self.assertEqual(json.loads(path.read_text()), original)
            newer = {**original, 'added_sids': ['s1', 's2']}
            path.write_text(json.dumps(newer))
            self.module.restore_seed_checkpoints(root, ['a'])
            self.assertEqual(json.loads(path.read_text()), newer)

    def test_context_index_never_copies_another_audits_profiles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'data/raw/federal_stance_context/index.json'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'a': {'s1': {'status': 'unavailable'}}, 'outside': {'s1': {'status': 'available'}}}))
            audit = {'target_ids': ['a'], 'profiles': {'a': {'contexts': {}}}}
            self.module.merge_contexts(root, audit)
            self.assertEqual(audit['profiles']['a']['contexts']['s1']['status'], 'unavailable')
            self.assertNotIn('outside', audit['profiles'])

    def test_seed_setup_failure_cannot_report_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            gaps = self.module.seed_gaps(Path(directory), ['a'])
            self.assertEqual(gaps, [{'id': 'a', 'error': 'missing_checkpoint', 'stage': 'setup'}])

    def test_old_seed_audit_cannot_hide_a_failed_new_invocation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.module.write(root / 'data/federal_seed_research.json', {'profiles': {'a': {'sources': {}, 'run_token': 'old'}}})
            self.assertEqual(self.module.seed_gaps(root, ['a'], 'new'),
                             [{'id': 'a', 'error': 'missing_current_checkpoint', 'stage': 'setup'}])

    def test_seed_model_failure_is_not_a_source_access_gap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.module.write(root / 'data/federal_seed_research.json', {'profiles': {'a': {'sources': {
                'https://a.gov': {'status': 'needs_retry', 'error': 'ValueError', 'error_stage': 'extract'}}}}})
            self.assertEqual(self.module.seed_gaps(root, ['a'])[0]['stage'], 'extract')

    def test_partial_seed_offsets_reset_without_matching_raw_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.module.write(root / 'data/federal_seed_research.json', {'profiles': {'a': {
                'sources': {'https://a.gov': {'status': 'needs_retry', 'next_chunk': 4}}, 'added_sids': ['s1']}}})
            self.module.restore_seed_checkpoints(root, ['a'])
            restored = self.module.read(root / 'data/raw/federal_research/a/seeds.json')
            self.assertEqual(restored['sources']['https://a.gov']['next_chunk'], 0)
            self.assertEqual(restored['added_sids'], ['s1'])


if __name__ == '__main__':
    unittest.main()
