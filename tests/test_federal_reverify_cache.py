import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class CachedReverificationTests(unittest.TestCase):
    def test_missing_cached_source_returns_an_incomplete_exit(self):
        import sys
        root_path = Path(__file__).resolve().parents[1]
        sys.path[:0] = [str(root_path / 'scripts'), str(root_path / 'scripts/daily')]
        import federal_reverify_cache as module
        with tempfile.TemporaryDirectory() as directory:
            report = {'paid_calls':0, 'added_sids':[], 'missing_pages':['seed-missing-0.json']}
            with patch.object(module, 'ROOT', Path(directory)), patch.object(module.policy_subjects, 'load_subjects', return_value=[{'id':'a','branch':'executive'}]), patch.object(module, 'reverify_subject', return_value=report), patch.object(sys, 'argv', ['reverify','--ids','a']):
                self.assertEqual(module.main(), 1)

    def test_first_invocation_saves_a_complete_audit(self):
        import sys
        root_path = Path(__file__).resolve().parents[1]
        sys.path[:0] = [str(root_path / 'scripts'), str(root_path / 'scripts/daily')]
        import federal_reverify_cache as module
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = {'paid_calls': 0, 'added_sids': ['s1']}
            with patch.object(module, 'ROOT', root), patch.object(module.policy_subjects, 'load_subjects', return_value=[{'id':'a','branch':'executive'}]), patch.object(module, 'reverify_subject', return_value=report), patch.object(sys, 'argv', ['reverify', '--ids', 'a']):
                module.main()
            saved = json.loads((root / 'data/federal_cached_reverification.json').read_text())
            self.assertEqual(saved['profiles']['a'], {**report, 'previous_attempts': []})

    def test_cached_rows_need_no_provider_and_keep_stable_ids(self):
        import sys
        root_path = Path(__file__).resolve().parents[1]
        sys.path[:0] = [str(root_path / 'scripts'), str(root_path / 'scripts/daily')]
        import federal_reverify_cache as module
        from test_federal_daily import PAGE, PERSON, ROW
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / 'data/raw/federal_research' / PERSON['id']; cache.mkdir(parents=True)
            digest = module.sources.digest(PAGE['url'])
            (cache / f'page-{digest}.json').write_text(json.dumps(PAGE))
            (cache / f'seed-{digest}-0.json').write_text(json.dumps([ROW]))
            (root / 'evidence').mkdir()
            (root / f"evidence/{PERSON['id']}.json").write_text('{"statements":[]}')
            with patch.object(module.sources, 'Client', side_effect=AssertionError('No provider calls')):
                first = module.reverify_subject(root, PERSON)
                second = module.reverify_subject(root, PERSON)
            self.assertEqual(first['added_sids'], ['s1'])
            self.assertEqual(second['added_sids'], [])
            self.assertEqual(first['paid_calls'], 0)
            saved = json.loads((root / f"evidence/{PERSON['id']}.json").read_text())['statements'][0]
            self.assertIsNone(saved['retrieved_on'])
            self.assertTrue(saved['reverified_on'])

    def test_missing_source_cache_never_creates_evidence(self):
        path = Path(__file__).resolve().parents[1] / 'scripts/federal_reverify_cache.py'
        self.assertTrue(path.exists())
        spec = importlib.util.spec_from_file_location('reverify', path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / 'data/raw/federal_research/a'; cache.mkdir(parents=True)
            (cache / 'seed-missing-0.json').write_text(json.dumps([{'subject_id':'a', 'quote':'An absent source cannot establish this official policy statement.'}]))
            (root / 'evidence').mkdir()
            (root / 'evidence/a.json').write_text('{"statements":[]}')
            report = module.reverify_subject(root, {'id':'a'})
            self.assertEqual(report['added_sids'], [])
            self.assertEqual(report['missing_pages'], ['seed-missing-0.json'])


if __name__ == '__main__':
    unittest.main()
