"""Exercise concurrent reservations against an in-memory provider ledger."""
from concurrent.futures import ThreadPoolExecutor, wait
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import sys
import math
from pathlib import Path

import llm
from model_budget import Budget
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/daily'))
import federal_sources


class ParallelBudgetTests(unittest.TestCase):
    def make_budget(self, gateway, metadata):
        budget = Budget(.8, False, metadata, gateway)
        budget.wait_for_capacity = True
        return budget

    def budget(self, cost=.01, failure=None):
        rows = []
        active = peak = calls = 0
        lock = threading.Lock()
        gateway = SimpleNamespace(
            BUDGETS={'openrouter': 500, 'monthly': {'openrouter': 35}},
            BudgetExceeded=llm.BudgetExceeded,
            PreflightBudgetExceeded=llm.PreflightBudgetExceeded,
            OpenRouterRequestError=llm.OpenRouterRequestError,
            spent=lambda _: sum(rows), spent_this_month=lambda _: sum(rows),
            _log=lambda provider, amount, tag, meta: rows.append(amount))
        def chat(messages, **kwargs):
            nonlocal active, peak, calls
            with lock:
                active += 1; peak = max(peak, active); calls += 1
            time.sleep(.02)
            with lock:
                active -= 1
            if failure:
                raise failure
            if cost is not None:
                rows.append(cost)
            return {'usage': {'cost': cost}, 'id': 'test'}
        gateway.chat = chat
        budget = self.make_budget(gateway, {'model': {'id': 'model', 'pricing': {'prompt': '.001', 'completion': '.001'}}})
        return budget, gateway, lambda: (peak, calls)

    def calls(self, budget):
        with ThreadPoolExecutor(max_workers=20) as pool:
            futures = [pool.submit(budget.call, 'model', [{'content': 'hello'}], 10, 'test') for _ in range(20)]
            done, pending = wait(futures, timeout=5)
            self.assertFalse(pending, 'Workers must wake when reservations settle')
        return futures

    def test_twenty_workers_wait_for_one_shared_allowance(self):
        budget, gateway, activity = self.budget()
        results = self.calls(budget)
        self.assertEqual([f.exception() for f in results], [None] * 20)
        self.assertEqual(activity(), (1, 20))
        self.assertAlmostEqual(gateway.spent('openrouter'), .2)

    def test_true_exhaustion_stops_waiters_without_extra_requests(self):
        budget, gateway, activity = self.budget(cost=.3)
        results = self.calls(budget)
        self.assertEqual(sum(f.exception() is None for f in results), 1)
        self.assertTrue(all(f.exception() is None or isinstance(f.exception(), llm.BudgetExceeded) for f in results))
        self.assertEqual(activity(), (1, 1))
        self.assertAlmostEqual(gateway.spent('openrouter'), .3)

    def test_unknown_cost_keeps_its_reservation_and_wakes_waiters(self):
        budget, gateway, activity = self.budget(cost=None)
        results = self.calls(budget)
        self.assertEqual(sum(f.exception() is None for f in results), 1)
        self.assertEqual(activity(), (1, 1))
        self.assertAlmostEqual(gateway.spent('openrouter'), .515)
        self.assertEqual(budget.uncertain, 1)

    def test_uncertain_failure_keeps_its_reservation_and_wakes_waiters(self):
        budget, gateway, activity = self.budget(failure=TimeoutError('provider response lost'))
        results = self.calls(budget)
        self.assertEqual(sum(isinstance(f.exception(), TimeoutError) for f in results), 1)
        self.assertEqual(activity(), (1, 1))
        self.assertAlmostEqual(gateway.spent('openrouter'), .515)

    def test_confirmed_preflight_rejections_release_waiting_capacity(self):
        rejection = llm.OpenRouterRequestError(402, {'message': 'busy', 'metadata': {'limit_source': 'openrouter_in_flight_budget'}})
        budget, gateway, activity = self.budget(failure=rejection)
        results = self.calls(budget)
        self.assertTrue(all(isinstance(f.exception(), llm.OpenRouterRequestError) for f in results))
        self.assertEqual(activity(), (1, 20))
        self.assertEqual(gateway.spent('openrouter'), 0)

    def test_monthly_limit_stops_before_transport(self):
        budget, gateway, activity = self.budget()
        getattr(budget, 'owner', budget).daily = True
        gateway.BUDGETS['monthly']['openrouter'] = .4
        with self.assertRaises(llm.BudgetExceeded):
            budget.call('model', [{'content': 'hello'}], 10, 'daily_test')
        self.assertEqual(activity(), (0, 0))

    def test_local_preflight_rejection_releases_an_unused_reservation(self):
        budget, gateway, _ = self.budget(failure=llm.PreflightBudgetExceeded('local cap'))
        with self.assertRaises(llm.PreflightBudgetExceeded):
            budget.call('model', [{'content': 'hello'}], 10, 'test')
        self.assertEqual(gateway.spent('openrouter'), 0)

    def test_nonfinite_ledger_fails_closed(self):
        budget, gateway, activity = self.budget()
        gateway.spent = lambda _: math.nan
        with self.assertRaises(ValueError):
            budget.call('model', [{'content': 'hello'}], 10, 'test')
        self.assertEqual(activity(), (0, 0))


class ParallelSourceBudgetTests(ParallelBudgetTests):
    def make_budget(self, gateway, metadata):
        gateway.os = SimpleNamespace(environ={'OPENROUTER_API_KEY': 'test'})
        response = SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'data': list(metadata.values())})
        with patch.dict(sys.modules, {'llm': gateway}), patch.object(federal_sources.httpx, 'get', return_value=response):
            client = federal_sources.Client(Path('.'), .8, model='model', daily=False, wait_for_capacity=True)
        # The source client's smaller fixed prompt margin needs a longer input
        # to produce the same hand-calculated $.515 reservation as inference.
        def call(model, messages, max_tokens, tag):
            return client.chat([{'content': 'hello' + 'x' * 300}], tag, max_tokens)
        return SimpleNamespace(call=call, client=client, owner=client.budget)

    def test_unknown_cost_keeps_its_reservation_and_wakes_waiters(self):
        budget, gateway, activity = self.budget(cost=None)
        results = self.calls(budget)
        self.assertEqual(sum(f.exception() is None for f in results), 1)
        self.assertEqual(activity(), (1, 1))
        self.assertAlmostEqual(gateway.spent('openrouter'), .515)

    def test_web_tool_parameters_and_timeout_survive_shared_accounting(self):
        budget, gateway, _ = self.budget()
        calls = []
        def chat(messages, **options):
            calls.append(options)
            return {'usage': {'cost': 0}}
        gateway.chat = chat
        tool = [{'type': 'openrouter:web_search', 'parameters': {
            'engine': 'exa', 'max_uses': 1, 'max_total_results': 1, 'max_characters': 20}}]
        budget.client.chat([{'content': 'hello'}], 'test', 10, tool)
        self.assertEqual(calls[0]['tools'], tool)
        self.assertNotIn('response_format', calls[0])
        self.assertEqual(calls[0]['retry_attempts'], 1)
        self.assertEqual(calls[0]['request_timeout'], 600)
        self.assertEqual(gateway.spent('openrouter'), 0)

    def test_request_fee_and_invalid_pricing_cannot_bypass_the_limit(self):
        budget, gateway, activity = self.budget()
        budget.client.metadata['pricing']['request'] = '.4'
        with self.assertRaises(llm.BudgetExceeded):
            budget.call('model', [{'content': 'hello'}], 10, 'test')
        budget.client.metadata['pricing']['request'] = 'nan'
        with self.assertRaises(ValueError):
            budget.call('model', [{'content': 'hello'}], 10, 'test')
        self.assertEqual(activity(), (0, 0))


if __name__ == '__main__':
    unittest.main()
