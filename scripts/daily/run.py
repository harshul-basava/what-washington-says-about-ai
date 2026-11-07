"""The daily update: collect -> label -> re-score -> detect changes -> snapshot -> rebuild site data.

Writes:
  data/changes.jsonl     every score change (kind "big" = 1+ point or crossing into/out of 3+, "small" = 0.5)
  data/last_run.json     what happened in this run (sources, counts, cost, changes)
  data/issue.md          GitHub issue body when there are big changes (the workflow opens the issue)

Usage: python scripts/daily/run.py [--sources x,crec,web] [--since YYYY-MM-DD] [--skip-collect] [--dry-run]
"""
import argparse
import json
import subprocess
import sys
import time

from common import ROOT, load_json, save_json, today
import collect
import history
import label
import llm
from phase3_label import DIMS, combine

CHANGES = ROOT / "data/changes.jsonl"
SUMM_MODEL = "deepseek/deepseek-v4.1-flash"
NAMES = {"ai_overall": "AI overall", "agi_pilled": "AGI", "x_risk": "x-risk", "china_race": "China race", "regulation": "Regulation"}
SUMM_PROMPT = """Here is the current summary of how {name} talks about AI, followed by their newest public statements.
Rewrite the summary in 2-4 plain sentences so it stays accurate with the new statements. Describe only what they say;
do not judge it. If the new statements change nothing, return the current summary unchanged.

Current summary:
{summary}

New statements:
{stmts}

Return only the summary text."""


def num(v):
    return v if isinstance(v, (int, float)) else None


def detect(old, new, labeled):
    """Compare published scores. labeled = {pid: [sids labeled this run]}."""
    daily = load_json(ROOT / "data/labels_daily.json", {})
    roster = {p["id"]: p for p in json.loads((ROOT / "data/roster.json").read_text())}
    out = []
    for pid, sc in new.items():
        for k in DIMS:
            a = num(((old.get(pid) or {}).get("dimensions", {}).get(k) or {}).get("score"))
            b = num((sc.get("dimensions", {}).get(k) or {}).get("score"))
            if a == b or (a is None and b is None):
                continue
            delta = (b or 0) - (a or 0)
            crossed = (a is not None and b is not None) and ((a >= 3) != (b >= 3))
            kind = "big" if abs(delta) >= 1 or crossed or (a is None) != (b is None) else "small"
            sids = [s for s in labeled.get(pid, []) if (daily.get(pid, {}).get(s) or {}).get("a", {}).get(k) is not None
                    or (daily.get(pid, {}).get(s) or {}).get("b", {}).get(k) is not None]
            p = roster.get(pid, {})
            out.append({"date": today(), "id": pid, "name": p.get("name"), "party": (p.get("party") or "?")[:1], "state": p.get("state"),
                        "dim": k, "old": a, "new": b, "kind": kind, "cause": "newly found statements" if sids else "older statements left the 24-month window",
                        "sids": sids, "human_reviewed": bool((sc.get("dimensions", {}).get(k) or {}).get("human"))})
    return out


def refresh_summaries(pids):
    f = ROOT / "data/summaries_daily.json"
    summ = load_json(f, {})
    scores = load_json(ROOT / "data/scores.json", {})
    log = [json.loads(x) for x in (ROOT / "data/new_statements.jsonl").read_text().splitlines()] if (ROOT / "data/new_statements.jsonl").exists() else []
    for pid in pids:
        ev = json.loads((ROOT / "evidence" / f"{pid}.json").read_text())
        new_sids = {r["sid"] for r in log if r["id"] == pid}
        stmts = [s for s in ev["statements"] if s["sid"] in new_sids][-15:]
        if not stmts:
            continue
        cur = (summ.get(pid) or {}).get("summary") or (scores.get(pid) or {}).get("summary") or "(no summary yet)"
        prompt = SUMM_PROMPT.format(name=ev["name"], summary=cur,
                                    stmts="\n".join(f"- ({s.get('date')}) {' '.join(s['text'].split())[:600]}" for s in stmts))
        try:
            d = llm.chat([{"role": "user", "content": prompt}], tag="daily_summary", model=SUMM_MODEL, max_tokens=600, temperature=0)
        except llm.BudgetExceeded:
            break
        text = (d["choices"][0]["message"]["content"] or "").strip()
        if 40 < len(text) < 1200:
            summ[pid] = {"summary": text, "updated": today()}
    save_json(f, summ, indent=1)


def issue_body(changes, report):
    big = [c for c in changes if c["kind"] == "big"]
    lines = [f"Daily update {today()}: {len(big)} big score change(s).", "",
             "| Member | Question | Old | New | Cause |", "|---|---|---|---|---|"]
    for c in big:
        f = lambda v: "n/a" if v is None else f"{v:g}"  # noqa: E731
        lines.append(f"| {c['name']} ({c['party']}-{c['state']}) | {NAMES[c['dim']]} | {f(c['old'])} | {f(c['new'])} | {c['cause']}"
                     + (f" ({', '.join(c['sids'])})" if c["sids"] else "") + (" · **human-reviewed score kept**" if c["human_reviewed"] else "") + " |")
    lines += ["", "To undo a change, add a decision to `data/human_review.json` (see `scripts/phase4_apply_review.py`).", "",
              f"Sources: {json.dumps(report.get('sources', {}))}", f"Spend this month: {json.dumps(report.get('spend_month', {}))}"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources")
    ap.add_argument("--since")
    ap.add_argument("--skip-collect", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    report = {"date": today()}
    if not a.skip_collect:
        args = (["--sources", a.sources] if a.sources else []) + (["--since", a.since] if a.since else []) + (["--dry-run"] if a.dry_run else [])
        report.update(collect.main(args))
    lab = label.main(["--dry-run"] if a.dry_run else [])
    report["labeling"] = lab["stats"]
    if a.dry_run:
        print(json.dumps(report, indent=1))
        return report
    old = load_json(ROOT / "data/scores.json", {})
    new = combine(today())
    changes = detect(old, new, lab["labeled"])
    with CHANGES.open("a") as fh:
        for c in changes:
            fh.write(json.dumps(c) + "\n")
    refresh_summaries(sorted({c["id"] for c in changes if c["kind"] == "big" and c["sids"]}))
    if any(c["kind"] == "big" for c in changes):
        combine(today())   # pick up refreshed summaries
    history.snapshot()
    history.build()
    subprocess.run([sys.executable, str(ROOT / "scripts/phase5_build_site.py")], check=True)
    report["changes"] = {"big": sum(c["kind"] == "big" for c in changes), "small": sum(c["kind"] == "small" for c in changes)}
    report["spend_month"] = {p: round(llm.spent_this_month(p), 2) for p in ("openrouter", "x", "exa")}
    report["seconds"] = round(time.time() - t0)
    save_json(ROOT / "data/last_run.json", report, indent=1)
    issue = ROOT / "data/issue.md"
    if report["changes"]["big"]:
        issue.write_text(issue_body(changes, report))
    elif issue.exists():
        issue.unlink()
    print(json.dumps(report, indent=1))
    return report


if __name__ == "__main__":
    main()
