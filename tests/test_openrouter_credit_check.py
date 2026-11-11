import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/openrouter_credit_check.py'


class CreditCheckTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(), 'The credit check script must exist')
        spec = importlib.util.spec_from_file_location('credit_check', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_all_limits_constrain_the_work(self):
        result = self.module.summarize(
            {'limit': 200, 'limit_remaining': 80,
             'effective_budget': {'remaining_usd': 60}},
            {'total_credits': 500, 'total_usage': 100},
            repository_remaining=185, required_credit=150)
        self.assertEqual(result['spendable_usd'], 60)
        self.assertFalse(result['enough_for_requested_work'])

    def test_unlimited_key_does_not_mean_unlimited_account(self):
        result = self.module.summarize(
            {'limit': None, 'limit_remaining': None},
            {'total_credits': 100, 'total_usage': 93.5},
            repository_remaining=185, required_credit=150)
        self.assertEqual(result['spendable_usd'], 6.5)
        self.assertFalse(result['enough_for_requested_work'])

    def test_ignores_secret_or_identity_fields(self):
        result = self.module.summarize(
            {'limit': None, 'limit_remaining': None,
             'label': 'SECRET', 'creator_user_id': 'PRIVATE'},
            {'total_credits': 500, 'total_usage': 100, 'secret': 'SECRET'},
            repository_remaining=185, required_credit=150)
        self.assertTrue(result['enough_for_requested_work'])
        self.assertNotIn('SECRET', str(result))
        self.assertNotIn('PRIVATE', str(result))

    def test_missing_or_invalid_credit_data_never_authorizes_spending(self):
        for credits in ({}, {'total_credits': True, 'total_usage': 0},
                        {'total_credits': float('nan'), 'total_usage': 0}):
            with self.subTest(credits=credits), self.assertRaises(ValueError):
                self.module.summarize({'limit': None, 'limit_remaining': None},
                                      credits, 185, 150)
        with self.assertRaises(ValueError):
            self.module.summarize({'limit': 100},
                                  {'total_credits': 500, 'total_usage': 0}, 185, 150)

    def test_invalid_or_inconsistent_key_cap_never_authorizes_spending(self):
        for limit in (False, 'invalid', float('nan'), -1, 100):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.module.summarize({'limit': limit, 'limit_remaining': 200},
                                      {'total_credits': 500, 'total_usage': 0}, 185, 150)

    def test_reports_budget_type_and_reset_without_identifiers(self):
        budget = {'scope': 'workspace', 'limit_usd': 320, 'remaining_usd': 8.32,
                  'reset_interval': 'monthly', 'resets_at': '2026-12-01T00:00:00Z',
                  'guardrail_id': 'PRIVATE', 'budget_id': 'PRIVATE'}
        result = self.module.summarize(
            {'limit': 500, 'limit_remaining': 188, 'budgets': [budget], 'effective_budget': budget},
            {'total_credits': 500, 'total_usage': 338}, 185, 150)
        self.assertEqual(len(result['guardrail_budgets']), 1)
        self.assertEqual(result['guardrail_budgets'][0]['scope'], 'workspace')
        self.assertEqual(result['guardrail_budgets'][0]['limit_usd'], 320)
        self.assertEqual(result['guardrail_budgets'][0]['reset_interval'], 'monthly')
        self.assertNotIn('PRIVATE', str(result))


if __name__ == '__main__':
    unittest.main()
