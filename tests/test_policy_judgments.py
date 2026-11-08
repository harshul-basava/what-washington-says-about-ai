import copy
import json
import tempfile
import unittest
from pathlib import Path

import policy_judgments as p


REGISTRY = {"version": 1, "policies": [{
    "id": "kill_switch_act_119", "title": "AI Kill Switch Act", "kind": "bill",
    "version": "introduced", "introduced": "2026-07-23", "source_url": "https://example.org/bill",
    "question": "Support this named bill?", "patterns": [r"AI Kill Switch Act", r"H\.?R\.?\s*9917"],
    "facets": [],
}]}
ITEM = {"key": "P|s1", "person_id": "P", "name": "Person", "sid": "s1",
        "text": "I support the AI Kill Switch Act.", "date": "2026-08-01", "context": "",
        "url": "https://example.org/quote", "source_type": "web", "verified_via": "ok",
        "targets": ["kill_switch_act_119"]}


def response(stance="support"):
    return {"judgments": [{"key": "P|s1", "targets": {"kill_switch_act_119": {
        "stance": stance, "reason": "The speaker explicitly supports the named bill.", "facets": []}}}]}


class PolicyTests(unittest.TestCase):
    def test_generic_car_switch_is_not_a_named_bill_candidate(self):
        self.assertEqual(p.match_targets({"text": "I oppose kill switches in cars.", "date": "2026-08-01"}, REGISTRY), [])
        self.assertEqual(p.match_targets(ITEM, REGISTRY), ["kill_switch_act_119"])

    def test_statement_before_policy_release_is_excluded(self):
        self.assertEqual(p.match_targets({**ITEM, "date": "2025-01-01"}, REGISTRY), [])
        self.assertEqual(p.match_targets({**ITEM, "date": "2026-07"}, REGISTRY), ["kill_switch_act_119"])

    def test_named_bills_match_official_numbers_without_short_titles(self):
        registry = p.load_registry(Path(__file__).resolve().parents[1])
        for number, target in [("H.R. 9925", "frontier_act_119"), ("H.R. 9917", "kill_switch_act_119"),
                               ("S. 1473", "stop_stealing_chips_119"), ("H.R. 6322", "stop_stealing_chips_119")]:
            with self.subTest(number=number):
                self.assertIn(target, p.match_targets({"text": "I introduced " + number, "date": "2026-07-23"}, registry))

    def test_missing_judgments_do_not_become_no_evidence(self):
        with self.assertRaises(ValueError):
            p.validate_response('{"judgments": []}', [ITEM], REGISTRY)

    def test_single_fenced_result_accepts_provider_prose_but_rejects_multiple_results(self):
        raw = 'Here is the assessment.\n\n```json\n' + json.dumps(response()) + '\n```'
        self.assertEqual(p.validate_response(raw, [ITEM], REGISTRY)["P|s1"]["kill_switch_act_119"]["stance"], "support")
        with self.assertRaises(ValueError):
            p.validate_response(raw + '\n```json\n' + json.dumps(response("oppose")) + '\n```', [ITEM], REGISTRY)
        with self.assertRaises(ValueError):
            p.validate_response('Assessment:\n```json\n{"judgments": []}\n```', [ITEM], REGISTRY)

    def test_unknown_or_duplicate_statement_is_rejected(self):
        raw = response()
        raw["judgments"][0]["key"] = "invented"
        with self.assertRaises(ValueError):
            p.validate_response(json.dumps(raw), [ITEM], REGISTRY)
        raw = response(); raw["judgments"] *= 2
        with self.assertRaises(ValueError):
            p.validate_response(json.dumps(raw), [ITEM], REGISTRY)

    def test_response_accepts_only_known_stances_and_facets(self):
        self.assertEqual(p.validate_response(json.dumps(response()), [ITEM], REGISTRY)["P|s1"]["kill_switch_act_119"]["stance"], "support")
        raw = response("probably_yes")
        with self.assertRaises(ValueError):
            p.validate_response(json.dumps(raw), [ITEM], REGISTRY)
        raw = response(); raw["judgments"][0]["targets"]["kill_switch_act_119"]["facets"] = ["invented"]
        with self.assertRaises(ValueError):
            p.validate_response(json.dumps(raw), [ITEM], REGISTRY)

    def test_cache_changes_with_evidence_registry_rubric_and_model(self):
        first = p.fingerprint([ITEM], REGISTRY, "rubric", "model-a")
        self.assertNotEqual(first, p.fingerprint([{**ITEM, "text": "I oppose it."}], REGISTRY, "rubric", "model-a"))
        reg = copy.deepcopy(REGISTRY); reg["policies"][0]["version"] = "amended"
        self.assertNotEqual(first, p.fingerprint([ITEM], reg, "rubric", "model-a"))
        self.assertNotEqual(first, p.fingerprint([ITEM], REGISTRY, "changed", "model-a"))
        self.assertNotEqual(first, p.fingerprint([ITEM], REGISTRY, "rubric", "model-b"))

    def test_conflicting_judges_remain_disputed(self):
        self.assertEqual(p.consensus({"a": {"stance": "support"}, "b": {"stance": "oppose"}}), "disputed")
        self.assertEqual(p.consensus({"a": {"stance": "support"}}), "pending")

    def test_facet_disagreement_needs_review_even_with_shared_stance(self):
        judges = {"a": {"stance": "support", "facets": ["competition_priority"]},
                  "b": {"stance": "support", "facets": ["competition_priority", "speed_over_safety"]}}
        self.assertTrue(p.facet_disagreement(judges))
        self.assertEqual(p.consensus(judges), "support")
        result = p.summarize([{"stance": "support", "facet_disagreement": True}], 1)
        self.assertTrue(result["review_required"])
        self.assertEqual(result["facet_disagreements"], 1)
        self.assertFalse(p.facet_disagreement({"a": judges["a"]}))

    def test_chart_records_preserve_agreed_and_disputed_facets(self):
        record = {"sid": "s1", "date": "2026", "stance": "support", "judges": {
            "a": {"facets": ["cooperation", "speed_over_safety"]},
            "b": {"facets": ["cooperation"]}}}
        chart = p.chart_record("P", record)
        self.assertEqual(chart["date"], "2026")
        self.assertEqual(chart["facets_agreed"], ["cooperation"])
        self.assertEqual(chart["facets_disputed"], ["speed_over_safety"])
        record["judges"].pop("b")
        record["stance"] = "pending"
        self.assertEqual(p.chart_record("P", record)["facets_agreed"], [])

    def test_conflicting_history_is_not_averaged_into_neutral(self):
        result = p.summarize([{"stance": "support", "date": "2025-01-01"}, {"stance": "oppose", "date": "2026-01-01"}], 2)
        self.assertEqual(result["stance"], "mixed")
        self.assertEqual(result["coverage"], "complete")

    def test_partial_or_missing_dates_never_imply_a_precise_latest_date(self):
        for dates, expected in [(["2026", "2026-10-21"], "2026"),
                                (["2026-12-31", "2026-12", "2026"], "2026"),
                                (["2026-08", "2026-09-01"], "2026-09-01"),
                                ([None, "2026-10-21"], None)]:
            with self.subTest(dates=dates):
                result = p.summarize([{"stance": "support", "date": d} for d in dates], len(dates))
                self.assertEqual(result["last_statement_date"], expected)
                self.assertEqual(result["has_undated_evidence"], None in dates)

    def test_no_candidates_differs_from_pending_and_irrelevant(self):
        self.assertEqual(p.summarize([], 0)["coverage"], "no_matching_evidence")
        self.assertEqual(p.summarize([], 2)["coverage"], "pending")
        self.assertEqual(p.summarize([{"stance": "not_relevant", "date": None}], 1)["coverage"], "no_relevant_evidence")
        self.assertEqual(p.summarize([{"stance": "support", "date": None}], 2)["coverage"], "partial")

    def test_offline_build_keeps_provenance_and_rejects_stale_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p.write_json(root / "config/policies.json", REGISTRY)
            (root / "config/policy_rubric.md").write_text("rubric")
            p.write_json(root / "data/roster.json", [{"id": "P", "name": "Person", "party": "Democrat", "state": "CA", "chamber": "house", "status": "current"}])
            stmt = {k: v for k, v in ITEM.items() if k in ("sid", "text", "date", "context", "url", "source_type", "verified_via")}
            stmt["verified"] = True
            p.write_json(root / "evidence/P.json", {"statements": [stmt]})
            saved = {"results": {"P|s1": {j: {"input_hash": p.fingerprint([ITEM], REGISTRY, "rubric", model), "labels": response()["judgments"][0]["targets"]} for j, model in p.JUDGES.items()}}}
            p.write_json(root / "data/policy_judgments.json", saved)
            result = p.build(root)
            self.assertEqual(result["members"][0]["policies"]["kill_switch_act_119"]["stance"], "support")
            detail = p.read_json(root / "site/data/policy_members/P.json")["policies"]["kill_switch_act_119"][0]
            self.assertEqual(detail["url"], "https://example.org/quote")
            self.assertEqual(set(detail["judges"]), {"sonnet", "gpt"})
            charts = p.read_json(root / "site/data/policy_charts.json")
            self.assertEqual(charts["revision"], result["chart_revision"])
            self.assertEqual(charts["policies"]["kill_switch_act_119"][0]["person_id"], "P")
            self.assertEqual(charts["policies"]["kill_switch_act_119"][0]["stance"], "support")
            old_revision = charts["revision"]
            stmt["text"] = "I oppose the AI Kill Switch Act."
            p.write_json(root / "evidence/P.json", {"statements": [stmt]})
            result = p.build(root)["members"][0]["policies"]["kill_switch_act_119"]
            self.assertEqual(result["coverage"], "pending")
            self.assertIsNone(result["stance"])
            charts = p.read_json(root / "site/data/policy_charts.json")
            self.assertNotEqual(charts["revision"], old_revision)
            self.assertEqual(charts["policies"]["kill_switch_act_119"][0]["stance"], "pending")

    def test_runner_is_read_only_without_label_command(self):
        import subprocess
        import sys
        result = subprocess.run([sys.executable, "scripts/phase3_policies.py", "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("plan", result.stdout)


if __name__ == "__main__":
    unittest.main()
