import contextlib
import importlib.util
import io
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_policy_judgments import ITEM, REGISTRY, response
import policy_judgments as p

spec = importlib.util.spec_from_file_location("policy_runner", Path(__file__).resolve().parents[1] / "scripts/phase3_policies.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
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
            args=SimpleNamespace(max_cost=budget,workers=1,batch_size=20)
            with self.subTest(budget=budget),tempfile.TemporaryDirectory() as tmp,patch.dict(sys.modules,{'llm':fake}),patch.object(runner,'ROOT',Path(tmp)),contextlib.redirect_stdout(io.StringIO()):
                saved={}
                runner.label_cascade([ITEM],saved,REGISTRY,'rubric','confidence',STRATEGY,args)
                self.assertEqual(len(calls),expected_calls)
                self.assertLessEqual(sum(costs),budget)
                self.assertEqual(cascade.resolve(ITEM,ITEM['targets'][0],saved,REGISTRY,'rubric','confidence',STRATEGY)['stance'],expected_stance)
                self.assertTrue((Path(tmp)/'data/policy_cascade.json').exists())
                self.assertFalse((Path(tmp)/'data/policy_judgments.json').exists())
