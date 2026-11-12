import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'scripts/daily'),
               str(Path(__file__).resolve().parents[1] / 'scripts')]
import history


class CongressHistoryTests(unittest.TestCase):
    def test_scored_counts_include_zero_and_exclude_unknown_or_invalid_scores(self):
        roster = [{'id': pid, 'party': party} for pid, party in
                  [('a', 'Democrat'), ('b', 'Republican'), ('c', 'Democrat'),
                   ('d', 'Independent'), ('e', 'Republican')]]
        scores = {'a': 0, 'b': 3, 'c': None, 'd': float('nan'), 'e': 'insufficient'}
        rows = history.summarize('2026-11-11', lambda pid, dim: scores[pid], roster,
                                 {'119': list(scores), '120': ['a', 'c']})
        rows = {(r['c'], r['p']): r for r in rows if r['k'] == 'x_risk'}
        self.assertEqual((rows['119', 'all']['n'], rows['119', 'all']['scored'],
                          rows['119', 'all']['hi'], rows['119', 'all']['mean']), (5, 2, 1, 1.5))
        self.assertEqual(rows['119', 'D']['scored'], 1)
        self.assertEqual(rows['119', 'R']['scored'], 1)
        self.assertEqual((rows['120', 'all']['n'], rows['120', 'all']['scored'],
                          rows['120', 'all']['hi']), (2, 1, 0))

    def test_daily_snapshot_and_build_preserve_the_scored_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'data').mkdir()
            (root / 'data/scores.json').write_text(json.dumps({
                'a': {'dimensions': {'x_risk': {'score': 0, 'reason_a': 'dismissive', 'reason_b': 'dismissive'}}},
                'b': {'dimensions': {'x_risk': {'score': 0, 'reason_a': 'silent', 'reason_b': 'silent'}}},
                'c': {'dimensions': {'x_risk': {'score': None}}}}))
            roster = [{'id': 'a', 'party': 'Democrat'}, {'id': 'b', 'party': 'Republican'},
                      {'id': 'c', 'party': 'Republican'}]
            with patch.object(history, 'ROOT', root), patch.object(history, 'HIST', root / 'data/history'), \
                 patch.object(history, 'cohorts', return_value=(roster, {'119': ['a', 'b', 'c']})), \
                 patch.object(history, 'today', return_value='2026-11-11'):
                history.snapshot()
                history.build()
            rows = json.loads((root / 'site/data/history.json').read_text())
            risk = next(r for r in rows if r['p'] == 'all' and r['k'] == 'x_risk')
            self.assertEqual((risk['n'], risk['scored'], risk['hi']), (3, 1, 0))
            unknown = next(r for r in rows if r['p'] == 'R' and r['k'] == 'x_risk')
            self.assertEqual((unknown['n'], unknown['scored'], unknown['hi']), (2, 0, 0))
