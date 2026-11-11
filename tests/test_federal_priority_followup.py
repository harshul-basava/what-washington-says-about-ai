import unittest


class PriorityFollowupTests(unittest.TestCase):
    def test_retry_allowance_counts_both_providers_and_keeps_context_reserve(self):
        from scripts.federal_priority_followup import allowances
        budget = {'openrouter_baseline': 100, 'x_baseline': 20, 'combined_limit': 18.90,
                  'x_search_limit': 2, 'astra_x_context_reserve': 1.50}
        self.assertEqual(allowances(budget, 100, 20)['x_search'], 2)
        self.assertAlmostEqual(allowances(budget, 106, 21)['models'], 10.4)
        self.assertAlmostEqual(allowances(budget, 117, 21)['models'], 0)
        self.assertEqual(allowances(budget, 110, 22)['x_search'], 0)
        with self.assertRaises(ValueError):
            allowances(budget, 99, 20)

    def test_name_variants_expand_mentions_without_claiming_account_ownership(self):
        from federal_stance_search import search_jobs
        subjects = {'a': {'id': 'a', 'name': 'James H. Adams', 'aliases': ['James Adams']}}
        job = search_jobs(subjects, [], '2026-11-11')[0]
        self.assertIn('("James H. Adams" OR "James Adams")', job['query'])
        self.assertEqual(job['kind'], 'mention')
        self.assertNotIn('from:', job['query'])

    def test_priority_queries_search_all_account_ai_posts_and_disambiguate_mentions(self):
        from federal_stance_search import search_jobs
        subjects = {'a': {'id': 'a', 'name': 'Official A'}, 'b': {'id': 'b', 'name': 'Common Name'}}
        accounts = [{'subject_id': 'a', 'handle': 'OfficialA', 'valid_from': '2025-01-01'}]
        jobs = search_jobs(subjects, accounts, '2026-11-11', broad_accounts=True,
                           mention_terms={'b': '(NIST OR standards)'})
        self.assertNotIn('OUTLOOK', jobs[0]['query'])
        self.assertNotIn('benefits', jobs[0]['query'])
        self.assertIn('(NIST OR standards)', jobs[-1]['query'])

