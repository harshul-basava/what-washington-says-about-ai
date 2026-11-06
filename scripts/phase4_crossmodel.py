"""Phase 4 (model review): a second model family checks the Sonnet scores.

  blind-submit   GPT re-scores everyone from scratch (same rubric + prompt, new shuffle), via batch
  blind-collect  poll + parse the blind batches -> data/raw/scores_xmodel/{id}.json
  audit          GPT sees Sonnet's scores + cited quotes and checks them. Covers the review packet plus
                 everyone where the blind score differs from Sonnet by >=2. Regular calls.
  report         review/crossmodel_report.md, plus reviewer_* columns in review/review_sheet.csv

The reviewer never changes data/scores.json. Disagreements are reported for a decision.
"""
import csv
import json
import statistics
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import llm  # noqa: E402
from phase3_score import BATCH_URL, DIMS, RUBRIC, build, parse, people, select  # noqa: E402
from phase4_review import spearman  # noqa: E402

REVIEWER = "openai/gpt-6.1-sol"
BLIND = ROOT / "data/raw/scores_xmodel"
AUDIT = ROOT / "data/raw/audit"
BATCHES = ROOT / "data/raw/xmodel_batches.json"
AUDIT_PROMPT = (ROOT / "config/audit_prompt.md").read_text().split("-->", 1)[1].strip()
for d in (BLIND, AUDIT):
    d.mkdir(parents=True, exist_ok=True)
HEAD = {"Authorization": f"Bearer {llm.os.environ['OPENROUTER_API_KEY']}"}


def num(v):
    return v if isinstance(v, (int, float)) else None


def blind_submit(chunk=150):
    todo = [ev for ev in people() if not (BLIND / f"{ev['id']}.json").exists()]
    est = sum(len(build(ev, 3)) / 3.5 for ev in todo) / 1e6 * 1.0 + len(todo) * 3000 / 1e6 * 5.0
    left = llm.BUDGETS["openrouter"] - llm.spent("openrouter")
    print(f"{len(todo)} requests, est ${est:.2f}, budget left ${left:.2f}")
    if est > left:
        raise SystemExit("would exceed budget")
    batches = json.loads(BATCHES.read_text()) if BATCHES.exists() else []
    for i in range(0, len(todo), chunk):
        part = todo[i:i + chunk]
        body = {"endpoint": "/v1/chat/completions", "model": REVIEWER, "completion_window": "24h", "requests": [
            {"custom_id": ev["id"], "body": {"messages": [{"role": "user", "content": build(ev, 3)}], "max_tokens": 8000}}
            for ev in part]}
        r = httpx.post(BATCH_URL, json=body, headers=HEAD, timeout=300)
        if r.status_code not in (200, 201, 202):
            raise SystemExit(f"batch submit failed {r.status_code}: {r.text[:500]}")
        batches.append({"id": r.json()["id"], "n": len(part), "logged": False})
        BATCHES.write_text(json.dumps(batches, indent=1))
        print("submitted", batches[-1]["id"], len(part))


def blind_collect():
    batches = json.loads(BATCHES.read_text())
    while True:
        pending = 0
        for b in batches:
            if b.get("final"):
                continue
            d = httpx.get(f"{BATCH_URL}/{b['id']}", headers=HEAD, timeout=120).json()
            st = d.get("status")
            if st not in ("completed", "failed", "expired", "cancelled"):
                pending += 1
                continue
            b["final"] = st
            for res in d.get("results") or []:
                if res.get("response") and res["response"].get("status_code") == 200:
                    parsed = parse(res["response"]["body"]["choices"][0]["message"]["content"])
                    if parsed:
                        (BLIND / f"{res['custom_id']}.json").write_text(json.dumps(parsed, indent=1))
            cost = float((d.get("usage") or {}).get("cost") or 0)
            if not b["logged"]:
                llm._log("openrouter", cost, "phase4_xmodel_batch", {"batch_id": b["id"], "status": st, "model": REVIEWER})
                b["logged"] = True
            print(b["id"], st, d.get("request_counts"), f"${cost:.2f}", flush=True)
        BATCHES.write_text(json.dumps(batches, indent=1))
        if not pending:
            break
        time.sleep(60)
    # anything the batch didn't return: regular calls
    for ev in people():
        if not (BLIND / f"{ev['id']}.json").exists():
            d = llm.chat([{"role": "user", "content": build(ev, 3)}], tag="phase4_xmodel_sync", model=REVIEWER)
            res = parse(d["choices"][0]["message"]["content"])
            if res:
                (BLIND / f"{ev['id']}.json").write_text(json.dumps(res, indent=1))
            print("sync", ev["id"], "ok" if res else "PARSE FAIL")


def blind_score(pid, k):
    f = BLIND / f"{pid}.json"
    return num(json.loads(f.read_text())["dimensions"][k]["score"]) if f.exists() else None


def audit_targets(scores):
    ids = {r["id"] for r in csv.DictReader(open(ROOT / "review/review_sheet.csv"))}
    for pid, s in scores.items():
        for k in DIMS:
            a, b = num(s.get("dimensions", {}).get(k, {}).get("score")), blind_score(pid, k)
            if a is not None and b is not None and abs(a - b) >= 2:
                ids.add(pid)
    return sorted(ids)


def audit():
    scores = json.loads((ROOT / "data/scores.json").read_text())
    evs = {ev["id"]: ev for ev in people()}
    targets = [p for p in audit_targets(scores) if not (AUDIT / f"{p}.json").exists()]
    print(f"auditing {len(targets)} people with {REVIEWER}")
    for pid in targets:
        ev, s = evs[pid], scores[pid]
        sids = {x["sid"] for x in select(ev["statements"])}
        cited = {sid for k in DIMS for sid in s["dimensions"][k].get("statement_ids", [])}
        # make sure every cited statement is in front of the reviewer
        st = list(select(ev["statements"])) + [x for x in ev["statements"] if x["sid"] in cited - sids]
        stmts = "\n".join(f"[{x['sid']}] ({x.get('date') or 'undated'}; {x['source_type']}) {' '.join(x['text'].split())[:700]}"
                          for x in sorted(st, key=lambda x: int(x["sid"][1:])))
        ratings = json.dumps({"summary": s.get("summary"), "dimensions": {
            k: {kk: s["dimensions"][k].get(kk) for kk in ("score", "justification", "statement_ids")} for k in DIMS}}, indent=1)
        prompt = AUDIT_PROMPT.format(rubric=RUBRIC, name=ev["name"], statements=stmts, ratings=ratings)
        d = llm.chat([{"role": "user", "content": prompt}], tag="phase4_audit", model=REVIEWER, max_tokens=6000)
        txt = d["choices"][0]["message"]["content"] or ""
        try:
            res = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
        except ValueError:
            print(pid, "PARSE FAIL")
            continue
        (AUDIT / f"{pid}.json").write_text(json.dumps(res, indent=1))
        dis = [k for k in DIMS if (res["dimensions"].get(k) or {}).get("verdict") == "disagree"]
        bad = [k for k in DIMS if (res["dimensions"].get(k) or {}).get("citations_support") is False]
        print(f"{ev['name']}: disagree={dis} bad_citations={bad} ${d['usage']['cost']:.3f}", flush=True)


def report():
    scores = json.loads((ROOT / "data/scores.json").read_text())
    roster = {p["id"]: p for p in json.loads((ROOT / "data/roster.json").read_text())}
    out = ["# Cross-model review (reviewer: " + REVIEWER + ")", "",
           "The reviewer is a different model family from the scorer (Claude Sonnet 5.5). It does two things: "
           "(1) **blind re-scoring** of everyone from the same evidence and rubric, and (2) an **audit**: it sees Sonnet's "
           "scores and cited quotes for the review packet, plus everyone whose blind score differs by ≥2, and checks them.", "",
           "## 1. Blind agreement (all scored people)", "",
           "| dimension | n (both scored) | exact | within 1 | Spearman ρ | Sonnet mean | reviewer mean | only one says insufficient |",
           "|---|---|---|---|---|---|---|---|"]
    for k in DIMS:
        pairs, one_ins = [], 0
        for pid, s in scores.items():
            a, b = num(s.get("dimensions", {}).get(k, {}).get("score")), blind_score(pid, k)
            if (BLIND / f"{pid}.json").exists() and (a is None) != (b is None):
                one_ins += 1
            if a is not None and b is not None:
                pairs.append((a, b))
        if not pairs:
            continue
        ex = sum(abs(a - b) <= 0.5 for a, b in pairs) / len(pairs)
        w1 = sum(abs(a - b) <= 1 for a, b in pairs) / len(pairs)
        rho = spearman([a for a, _ in pairs], [b for _, b in pairs])
        out.append(f"| {k} | {len(pairs)} | {ex:.0%} | {w1:.0%} | {rho:.2f} | {statistics.mean(a for a, _ in pairs):.2f} | "
                   f"{statistics.mean(b for _, b in pairs):.2f} | {one_ins} |")
    out += ["", "\"Exact\" means within 0.5, because Sonnet's score is an average of two runs.", ""]

    audits = {f.stem: json.loads(f.read_text()) for f in AUDIT.glob("*.json")}
    n_dim = sum(1 for a in audits.values() for k in DIMS if a["dimensions"].get(k))
    n_dis = sum(1 for a in audits.values() for k in DIMS if (a["dimensions"].get(k) or {}).get("verdict") == "disagree")
    n_bad = sum(1 for a in audits.values() for k in DIMS if (a["dimensions"].get(k) or {}).get("citations_support") is False)
    n_sum = sum(1 for a in audits.values() if a.get("summary_ok") is False)
    out += ["## 2. Audit", "", f"{len(audits)} people, {n_dim} person-dimensions. The reviewer disagreed on **{n_dis}** "
            f"({n_dis / max(n_dim, 1):.0%}), flagged citations as not supporting the score on **{n_bad}**, and flagged "
            f"**{n_sum}** summaries.", "", "### Disagreements and citation problems", ""]
    for pid in sorted(audits, key=lambda p: roster[p]["name"]):
        a, s, p = audits[pid], scores[pid], roster[pid]
        lines = []
        for k in DIMS:
            r = a["dimensions"].get(k) or {}
            if r.get("verdict") == "disagree" or r.get("citations_support") is False:
                tag = []
                if r.get("verdict") == "disagree":
                    tag.append(f"Sonnet {s['dimensions'][k]['score']} → reviewer {r.get('your_score')}")
                if r.get("citations_support") is False:
                    tag.append(f"bad citations {', '.join(r.get('bad_citations') or [])}")
                lines.append(f"- **{k}** ({'; '.join(tag)}): {r.get('note', '')}")
        if a.get("summary_ok") is False:
            lines.append(f"- **summary**: {a.get('summary_note', '')}")
        if lines:
            out += [f"**{p['name']}** ({p['party']}, {p['state']})", ""] + lines + [""]
    (ROOT / "review/crossmodel_report.md").write_text("\n".join(out))

    sheet = ROOT / "review/review_sheet.csv"
    rows = list(csv.DictReader(open(sheet)))
    for r in rows:
        a = (audits.get(r["id"]) or {}).get("dimensions", {}).get(r["dimension"]) or {}
        r["reviewer_score"] = a.get("your_score", "")
        r["reviewer_verdict"] = a.get("verdict", "")
        r["reviewer_citations_ok"] = a.get("citations_support", "")
        r["reviewer_note"] = a.get("note", "")
        r["blind_score"] = blind_score(r["id"], r["dimension"]) if blind_score(r["id"], r["dimension"]) is not None else ""
    with open(sheet, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"report written: {len(audits)} audited, {n_dis} disagreements, {n_bad} citation problems, {n_sum} summaries")


if __name__ == "__main__":
    {"blind-submit": blind_submit, "blind-collect": blind_collect, "audit": audit, "report": report}[sys.argv[1]]()
