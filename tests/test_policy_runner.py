import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_policy_judgments import ITEM, REGISTRY, response
from test_policy_subjects import ATTRIBUTION, SUBJECTS
import policy_judgments as p

spec = importlib.util.spec_from_file_location("policy_runner", Path(__file__).resolve().parents[1] / "scripts/phase3_policies.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def persistent_gateway(fake, costs=None):
    """Test gateway with the same reservation ledger and usage-cost contract as llm."""
    from llm import BudgetExceeded
    charges = costs if costs is not None else []
    original_spent = fake.spent
    original_month = getattr(fake, 'spent_this_month', lambda provider: 0)
    if costs is None:
        fake.spent = lambda provider: original_spent(provider) + sum(charges)
        fake.spent_this_month = lambda provider: original_month(provider) + sum(charges)
    fake._log = lambda provider, cost, tag, meta: charges.append(cost)
    fake.BudgetExceeded = BudgetExceeded
    original_chat = fake.chat
    def chat(*args, **kwargs):
        before = fake.spent('openrouter')
        result = original_chat(*args, **kwargs)
        result['usage'] = {'cost': max(0, fake.spent('openrouter') - before)}
        return result
    fake.chat = chat
    return fake


class RunnerTests(unittest.TestCase):
    def test_default_federal_budget_can_reserve_an_astra_review(self):
        import json
        import policy_cascade as cascade
        from test_policy_cascade import STRATEGY, label
        costs, calls = [], []
        def chat(messages, **kwargs):
            role = 'deepseek' if kwargs['model'] == 'deepseek/test' else 'astra'
            calls.append(role); costs.append(0.01)
            value = label('support', 0.7 if role == 'deepseek' else 0.95)
            return {'choices': [{'message': {'content': json.dumps({'judgments': [{'key': ITEM['key'], 'targets': {ITEM['targets'][0]: value}}]})}}]}
        metadata = {'data': [{'id': model, 'pricing': {'prompt': '0.00001', 'completion': '0.00005',
            'overrides': [{'prompt': '0.00002', 'completion': '0.000075'}]}} for model in cascade.models(STRATEGY).values()]}
        fake = SimpleNamespace(os=SimpleNamespace(environ={'OPENROUTER_API_KEY': 'test-only'}),
            httpx=SimpleNamespace(get=lambda *a, **k: SimpleNamespace(raise_for_status=lambda: None, json=lambda: metadata)),
            spent=lambda provider: sum(costs), spent_this_month=lambda provider: sum(costs),
            BUDGETS={'openrouter': 10, 'monthly': {'openrouter': 5}}, chat=chat)
        persistent_gateway(fake, costs)
        config = json.loads((Path(__file__).resolve().parents[1] / 'config/federal_sources.json').read_text())
        args = SimpleNamespace(max_cost=config['judgment_max_cost'], workers=1, batch_size=1, daily=True)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {'llm': fake}), patch.object(runner, 'ROOT', Path(tmp)), contextlib.redirect_stdout(io.StringIO()):
            runner.label_cascade([ITEM], {}, REGISTRY, 'rubric', 'confidence', STRATEGY, args)
        self.assertEqual(calls, ['deepseek', 'astra'])

    def test_scope_selects_registered_executive_ids_only(self):
        items = [ITEM, {**ITEM, 'person_id': 'official_a'}, {**ITEM, 'person_id': 'agency_a'}]
        subjects = [{'id': ITEM['person_id'], 'branch': 'legislative'},
                    {'id': 'official_a', 'branch': 'executive'}, {'id': 'agency_a', 'branch': 'executive'}]
        self.assertEqual([s['person_id'] for s in runner.select_scope(items, subjects, 'executive')], ['official_a', 'agency_a'])
        self.assertEqual(runner.select_scope(items, subjects, 'all'), items)

    def test_cohort_plan_reads_only_selected_subject_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p.write_json(root / 'config/policy_subjects.json', SUBJECTS)
            p.write_json(root / 'config/policies.json', REGISTRY)
            (root / 'config/policy_rubric.md').write_text('rubric')
            p.write_json(root / 'data/roster.json', [{'id': 'P', 'name': 'Person'}])
            p.write_json(root / 'evidence/executive_a.json', {'statements': [ITEM | {
                'verified': True, 'attribution': ATTRIBUTION}]})
            p.write_json(root / 'evidence/commerce.json', {'statements': []})
            (root / 'evidence/P.json').write_text('invalid outside the cohort')

            for ids, statements in [('executive_a', 1), ('commerce', 0)]:
                with self.subTest(ids=ids), patch.object(runner, 'ROOT', root), patch.object(sys, 'argv', [
                    'phase3_policies.py', 'plan', '--scope', 'executive', '--ids', ids,
                    '--targets', 'kill_switch_act_119',
                ]), contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()) as errors:
                    try:
                        runner.main()
                    except SystemExit as exc:
                        self.fail(f'Expected an offline plan, got exit {exc.code}: {errors.getvalue()}')
                    report = json.loads(output.getvalue())
                    self.assertEqual(report['candidate_statements'], statements)
                    self.assertEqual(report['people'], statements)

            with patch.object(runner, 'ROOT', root), patch.object(sys, 'argv', [
                'phase3_policies.py', 'label', '--scope', 'executive', '--ids', 'unknown',
            ]), contextlib.redirect_stderr(io.StringIO()) as output, self.assertRaises(SystemExit) as raised:
                runner.main()
            self.assertEqual(raised.exception.code, 2)
            self.assertIn('Unknown subject ID', output.getvalue())

    def test_daily_judgments_reserve_monthly_budget_and_use_daily_tags(self):
        import json
        metadata = {'data': [{'id': model, 'pricing': {'prompt': '0', 'completion': '0.00001'}} for model in p.JUDGES.values()]}
        for month_spent, expected in [(0.95, 0), (0.80, 1)]:
            calls = []
            def chat(*args, **kwargs):
                calls.append(kwargs['tag'])
                return {'choices': [{'message': {'content': json.dumps(response())}}]}
            fake = SimpleNamespace(os=SimpleNamespace(environ={'OPENROUTER_API_KEY': 'test-only'}),
                httpx=SimpleNamespace(get=lambda *a, **k: SimpleNamespace(raise_for_status=lambda: None, json=lambda: metadata)),
                spent=lambda provider: 0, spent_this_month=lambda provider: month_spent,
                BUDGETS={'openrouter': 10, 'monthly': {'openrouter': 1}}, chat=chat)
            persistent_gateway(fake)
            with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {'llm': fake}), patch.object(runner, 'ROOT', Path(tmp)), contextlib.redirect_stdout(io.StringIO()):
                runner.label([(next(iter(p.JUDGES)), [ITEM])], {}, REGISTRY, 'rubric', SimpleNamespace(max_cost=1, workers=1, daily=True))
            self.assertEqual(len(calls), expected)
            self.assertTrue(all(tag.startswith('daily_') for tag in calls))

    def test_invalid_spending_limits_fail_before_network_access(self):
        for limit in [float("nan"), float("inf"), -1, 0]:
            with self.subTest(limit=limit), patch.dict(sys.modules, {"llm": SimpleNamespace()}):
                with self.assertRaises(ValueError):
                    runner.label([], {}, REGISTRY, "rubric", SimpleNamespace(max_cost=limit, workers=2))

    def test_concurrent_calls_reserve_budget_and_save_only_complete_results(self):
        import json
        costs, calls = [], []
        gate = threading.Event()

        def chat(*args, **kwargs):
            calls.append(kwargs["model"])
            gate.wait(0.05)  # The other worker must observe this call's reservation.
            costs.append(0.1)
            return {"choices": [{"message": {"content": json.dumps(response())}}]}

        metadata = {"data": [{"id": model, "pricing": {"prompt": "0", "completion": "0.00001"}}
                             for model in p.JUDGES.values()]}
        fake = SimpleNamespace(
            os=SimpleNamespace(environ={"OPENROUTER_API_KEY": "test-only"}),
            httpx=SimpleNamespace(get=lambda *a, **k: SimpleNamespace(raise_for_status=lambda: None, json=lambda: metadata)),
            spent=lambda provider: sum(costs), BUDGETS={"openrouter": 2}, chat=chat)
        persistent_gateway(fake, costs)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {"llm": fake}), patch.object(runner, "ROOT", Path(tmp)), contextlib.redirect_stdout(io.StringIO()):
            saved = {"results": {}}
            errors = runner.label([(j, [ITEM]) for j in p.JUDGES], saved, REGISTRY, "rubric", SimpleNamespace(max_cost=0.15, workers=2))
            self.assertEqual(errors, 1)
            self.assertEqual(len(calls), 1)
            self.assertLessEqual(sum(costs), 0.15)
            self.assertEqual(len(saved["results"][ITEM["key"]]), 1)
            self.assertEqual(p.read_json(Path(tmp) / "data/policy_judgments.json"), saved)
            remaining = runner.jobs([ITEM], saved, REGISTRY, "rubric", 20)
            self.assertEqual(len(remaining), 1)

    def test_cascade_routes_review_and_shares_spending_limit_between_stages(self):
        import json
        import policy_cascade as cascade
        from test_policy_cascade import STRATEGY, label
        for budget, expected_calls, expected_stance in [(0.15,1,'pending'),(0.30,2,'oppose')]:
            costs, calls=[],[]
            def chat(messages, **kwargs):
                role='deepseek' if kwargs['model']=='deepseek/test' else 'astra'
                calls.append(role)
                costs.append(0.1)
                value=label('support',0.7) if role=='deepseek' else label('oppose',0.95)
                return {'id':'gen-test','choices':[{'message':{'content':json.dumps({'judgments':[{'key':ITEM['key'],'targets':{ITEM['targets'][0]:value}}]})}}]}
            metadata={'data':[{'id':model,'pricing':{'prompt':'0','completion':'0.00001'},'supported_parameters':['response_format','max_tokens','reasoning']} for model in cascade.models(STRATEGY).values()]}
            fake=SimpleNamespace(os=SimpleNamespace(environ={'OPENROUTER_API_KEY':'test-only'}),
                httpx=SimpleNamespace(get=lambda *a,**k:SimpleNamespace(raise_for_status=lambda:None,json=lambda:metadata)),
                spent=lambda provider:sum(costs),BUDGETS={'openrouter':2},chat=chat)
            persistent_gateway(fake, costs)
            args=SimpleNamespace(max_cost=budget,workers=1,batch_size=20)
            with self.subTest(budget=budget),tempfile.TemporaryDirectory() as tmp,patch.dict(sys.modules,{'llm':fake}),patch.object(runner,'ROOT',Path(tmp)),contextlib.redirect_stdout(io.StringIO()):
                saved={}
                runner.label_cascade([ITEM],saved,REGISTRY,'rubric','confidence',STRATEGY,args)
                self.assertEqual(len(calls),expected_calls)
                self.assertLessEqual(sum(costs),budget)
                self.assertEqual(cascade.resolve(ITEM,ITEM['targets'][0],saved,REGISTRY,'rubric','confidence',STRATEGY)['stance'],expected_stance)
                self.assertTrue((Path(tmp)/'data/policy_cascade.json').exists())
                self.assertFalse((Path(tmp)/'data/policy_judgments.json').exists())

    def test_uncertain_policy_request_keeps_a_persistent_charge(self):
        import json
        import httpx
        import llm
        metadata={'data':[{'id':model,'pricing':{'prompt':'0.000001','completion':'0.00001'}} for model in p.JUDGES.values()]}
        response_meta=SimpleNamespace(raise_for_status=lambda:None,json=lambda:metadata)
        with tempfile.TemporaryDirectory() as tmp, patch.object(llm,'LEDGER',Path(tmp)/'costs.jsonl'), \
             patch.object(llm,'BUDGETS',{'openrouter':10}),patch.dict(llm.os.environ,{'OPENROUTER_API_KEY':'test'}), \
             patch.object(llm.httpx,'get',return_value=response_meta), \
             patch.object(llm.httpx,'post',side_effect=httpx.ReadTimeout('timeout')) as post, \
             patch.object(runner,'ROOT',Path(tmp)),contextlib.redirect_stdout(io.StringIO()):
            errors=runner.label([('sonnet',[ITEM])],{},REGISTRY,'rubric',SimpleNamespace(max_cost=1,workers=1))
            self.assertEqual(errors,1);self.assertEqual(post.call_count,1)
            records=[json.loads(line) for line in llm.LEDGER.read_text().splitlines()]
            self.assertEqual(len(records),1);self.assertEqual(records[0]['phase'],'reservation')
            self.assertTrue(records[0]['cost_uncertain']);self.assertGreater(llm.spent('openrouter'),0)
