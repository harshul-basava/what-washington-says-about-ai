import importlib.util
import json
from pathlib import Path
import unittest

import httpx


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/openrouter_workspace_budget.py'
WORKSPACE = '11111111-1111-4111-8111-111111111111'


class WorkspaceBudgetTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(), 'The authorized budget updater must exist')
        spec = importlib.util.spec_from_file_location('workspace_budget', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def client(self, cap=200, denied=False, missing_identity=False, malformed_other=False):
        self.requests = []
        current = [cap]

        def respond(request):
            self.requests.append(request)
            if request.url.path == '/api/v1/key':
                return httpx.Response(200, json={'data': {
                    'workspace_id': WORKSPACE,
                    'budgets': [{'scope': 'workspace', 'budget_id': None if missing_identity else 'budget-1',
                                 'limit_usd': current[0], 'reset_interval': None}]}})
            if denied:
                return httpx.Response(403, json={'error': 'provider detail must stay private'})
            if request.method == 'PUT':
                current[0] = json.loads(request.content)['limit_usd']
                return httpx.Response(200, json={'data': {}})
            return httpx.Response(200, json={'data': [
                {'id': None if missing_identity else 'budget-1', 'workspace_id': WORKSPACE, 'limit_usd': current[0], 'reset_interval': None},
                {'id': None if malformed_other else 'budget-2', 'workspace_id': WORKSPACE, 'limit_usd': 30, 'reset_interval': 'daily'}]})

        return httpx.Client(transport=httpx.MockTransport(respond))

    def test_changes_only_existing_lifetime_cap_to_350(self):
        with self.client() as client:
            result = self.module.raise_workspace_cap(client)
        changes = [r for r in self.requests if r.method != 'GET']
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].method, 'PUT')
        self.assertEqual(changes[0].url.path, f'/api/v1/workspaces/{WORKSPACE}/budgets/lifetime')
        self.assertEqual(json.loads(changes[0].content), {'limit_usd': 350})
        self.assertEqual(result['status'], 'updated')
        self.assertNotIn(WORKSPACE, json.dumps(result))

    def test_retry_does_not_change_an_already_350_cap(self):
        with self.client(cap=350) as client:
            self.assertEqual(self.module.raise_workspace_cap(client)['status'], 'already_set')
        self.assertFalse(any(r.method != 'GET' for r in self.requests))

    def test_unexpected_cap_never_triggers_a_write(self):
        with self.client(cap=500) as client, self.assertRaises(ValueError):
            self.module.raise_workspace_cap(client)
        self.assertFalse(any(r.method != 'GET' for r in self.requests))

    def test_missing_management_access_never_triggers_a_write(self):
        with self.client(denied=True) as client, self.assertRaises(self.module.MetadataError) as raised:
            self.module.raise_workspace_cap(client)
        self.assertEqual(raised.exception.status_code, 403)
        self.assertNotIn('provider detail', str(raised.exception))
        self.assertFalse(any(r.method != 'GET' for r in self.requests))

    def test_missing_budget_ids_never_trigger_a_write(self):
        with self.client(missing_identity=True) as client, self.assertRaises(ValueError):
            self.module.raise_workspace_cap(client)
        self.assertFalse(any(r.method != 'GET' for r in self.requests))

    def test_malformed_other_intervals_fail_before_a_write(self):
        with self.client(malformed_other=True) as client, self.assertRaises(ValueError):
            self.module.raise_workspace_cap(client)
        self.assertFalse(any(r.method != 'GET' for r in self.requests))


if __name__ == '__main__':
    unittest.main()
