"""Build site/data/review.json for the temporary human-review page (site/review.html).

One item per (person, question), ordered by how much it needs a human:
  1 no_support   the auditor says none of the cited quotes support the score
  2 disagree     the auditor would give a different score
  3 runs_split   the two scoring runs differed by 2+
  4 blind_gap    the blind second-model score differs by 2+
  5 packet       top x-risk / AGI scorers and the random sample (review/review_sheet.csv)
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIMS = ["ai_overall", "agi_pilled", "x_risk", "china_race", "regulation"]
num = lambda v: v if isinstance(v, (int, float)) else None  # noqa: E731


def main():
    roster = {p["id"]: p for p in json.loads((ROOT / "data/roster.json").read_text())}
    scores = json.loads((ROOT / "data/scores.json").read_text())
    audits = {f.stem: json.loads(f.read_text()) for f in (ROOT / "data/raw/audit").glob("*.json")}
    blind = {f.stem: json.loads(f.read_text()) for f in (ROOT / "data/raw/scores_xmodel").glob("*.json")}
    packet = {(r["id"], r["dimension"]): r["why"] for r in csv.DictReader(open(ROOT / "review/review_sheet.csv"))}
    items = []
    for pid, s in scores.items():
        if pid not in roster or not s.get("summary"):
            continue
        p = roster[pid]
        for k in DIMS:
            d = s["dimensions"][k]
            a = (audits.get(pid) or {}).get("dimensions", {}).get(k) or {}
            b = num(((blind.get(pid) or {}).get("dimensions", {}).get(k) or {}).get("score"))
            sc, cited, bad = num(d.get("score")), d.get("statement_ids") or [], a.get("bad_citations") or []
            cats = []
            if a and cited and set(cited) <= set(bad):
                cats.append("no_support")
            if a.get("verdict") == "disagree":
                cats.append("disagree")
            ra, rb = num(d.get("run_a")), num(d.get("run_b"))
            if ra is not None and rb is not None and abs(ra - rb) >= 2:
                cats.append("runs_split")
            if sc is not None and b is not None and abs(sc - b) >= 2:
                cats.append("blind_gap")
            why = packet.get((pid, k), "")
            # packet: top scorers on the question they top, plus every question for the random sample
            if (why == "top x-risk" and k == "x_risk") or (why == "top AGI-pilled" and k == "agi_pilled") or why == "random":
                cats.append("packet")
            if not cats:
                continue
            items.append({
                "id": pid, "name": p["name"], "party": p["party"][:1], "state": p["state"], "chamber": p["chamber"],
                "status": p["status"], "dim": k, "cats": cats, "why": packet.get((pid, k), ""),
                "score": d.get("score"), "run_a": d.get("run_a"), "run_b": d.get("run_b"),
                "justification": d.get("justification"), "cited": cited, "summary": s.get("summary"),
                "blind": ((blind.get(pid) or {}).get("dimensions", {}).get(k) or {}).get("score"),
                "audit": {"verdict": a.get("verdict"), "score": a.get("your_score"), "citations_ok": a.get("citations_support"),
                          "bad": bad, "note": a.get("note")} if a else None,
            })
    order = ["no_support", "disagree", "runs_split", "blind_gap", "packet"]
    items.sort(key=lambda x: (min(order.index(c) for c in x["cats"]), x["name"], DIMS.index(x["dim"])))
    (ROOT / "site/data/review.json").write_text(json.dumps(items))
    from collections import Counter
    print(len(items), "items", Counter(order[min(order.index(c) for c in x["cats"])] for x in items))


if __name__ == "__main__":
    main()
