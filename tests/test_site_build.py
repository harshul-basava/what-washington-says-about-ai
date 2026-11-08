"""Exercise the same offline website entry point used by the daily job."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import policy_cascade as cascade
import policy_judgments as policy
from test_policy_cascade import STRATEGY, label
from test_policy_judgments import ITEM, REGISTRY


class SiteBuildTests(unittest.TestCase):
    def test_daily_site_build_preserves_scores_and_refreshes_policy_evidence(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('Makefile', 'scripts/phase5_build_site.py', 'policy_judgments.py', 'policy_cascade.py', 'policy_subjects.py', 'federal_coverage.py'):
                dest = root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(repo / name, dest)
            (root / 'llm.py').write_text("raise AssertionError('Offline build imported the paid gateway')\n")
            person = dict(id='P', name='Person', party='Democrat', state='CA', chamber='house',
                          status='current', district=1)
            policy.write_json(root / 'data/roster.json', [person])
            policy.write_json(root / 'data/scores.json', {'P': {'dimensions': {'china_race': {'score': 3}}}})
            policy.write_json(root / 'data/ref/legislators-current.json', [])
            policy.write_json(root / 'data/ref/committee-membership-current.json', {})
            for name in ('sponsorshipanalysis_h.txt', 'sponsorshipanalysis_s.txt'):
                (root / 'data/ref' / name).write_text('ID,ideology\n')
            policy.write_json(root / 'data/labels_daily.json', {'P': {'s1': {
                'a': {'china_race': 3}, 'b': {'china_race': 3},
                'models': {'a': 'DeepSeek V4.1 Flash', 'b': 'GPT-6.1 Sol'}}}})
            policy.write_json(root / 'config/policies.json', REGISTRY)
            policy.write_json(root / 'config/policy_judging.json', STRATEGY)
            (root / 'config/policy_rubric.md').write_text('rubric')
            (root / 'config/policy_confidence.md').write_text('confidence')
            evidence = {'name': 'Person', 'statements': [{**ITEM, 'verified': True}]}
            policy.write_json(root / 'evidence/P.json', evidence)
            saved = {}
            cascade.save_result(saved, ITEM, ITEM['targets'][0], 'deepseek', label(),
                                REGISTRY, 'rubric', 'confidence', STRATEGY, 'test-generation')
            policy.write_json(root / 'data/policy_cascade.json', saved)

            def build():
                result = subprocess.run([sys.executable, str(root / 'scripts/phase5_build_site.py')],
                                        cwd=root, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

            build()
            self.assertTrue((root / 'site/data/policies.json').exists(),
                            'The daily website build must also export policy judgments')
            members = policy.read_json(root / 'site/data/members.json')['members']
            self.assertEqual(members[0]['scores']['china_race'], 3)
            quotes = policy.read_json(root / 'site/data/quotes/P.json')['quotes']
            self.assertEqual(quotes[0]['by'], ['DeepSeek V4.1 Flash', 'GPT-6.1 Sol'])
            rows = policy.read_json(root / 'site/data/policy_members/P.json')['policies'][ITEM['targets'][0]]
            self.assertEqual(rows[0]['stance'], 'support')

            evidence['statements'][0]['text'] = 'I oppose the AI Kill Switch Act.'
            policy.write_json(root / 'evidence/P.json', evidence)
            build()
            rows = policy.read_json(root / 'site/data/policy_members/P.json')['policies'][ITEM['targets'][0]]
            self.assertEqual(rows[0]['text'], evidence['statements'][0]['text'])
            self.assertEqual(rows[0]['review_status'], 'awaiting_deepseek')
            result = subprocess.run(['make', 'site', f'PY={sys.executable}'],
                                    cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
