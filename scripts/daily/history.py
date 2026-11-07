"""Score history: share of members at 3+ per question, party and Congress, over time.

  backfill  replay the fixed scoring formula with each month-end as the cutoff (only statements dated on or before it,
            recency window relative to it), from 2023-01 to the snapshot date -> data/history/backfill.json
  snapshot  today's published scores -> data/history/YYYY-MM-DD.json (run by the daily job)
  build     merge both into site/data/history.json

Usage: python scripts/daily/history.py backfill|snapshot|build
"""
import json
import sys
from datetime import date, timedelta

from common import ROOT, SNAPSHOT_DATE, load_json, save_json, today
from phase3_label import DIMS, LABELS_BASE, LABELS_DAILY, judge_labels, recent_cutoff, score_member

HIST = ROOT / "data/history"
PARTY = lambda p: "D" if (p or "").lower().startswith("dem") else "R" if (p or "").lower().startswith("rep") else "I"  # noqa: E731


def cohorts():
    """{"119": [ids], "120": [ids]} using the same rule as the site."""
    nxt = load_json(ROOT / "data/next_congress.json", {})
    roster = json.loads((ROOT / "data/roster.json").read_text())
    c119 = [p["id"] for p in roster if p["status"] == "current"]
    c120 = [p["id"] for p in roster if (nxt.get(p["id"]) or {}).get("status") in ("continuing", "arriving")]
    return roster, {"119": c119, "120": c120}


def summarize(day, score_of, roster, groups):
    party = {p["id"]: PARTY(p["party"]) for p in roster}
    rows = []
    for cong, ids in groups.items():
        for pa in ("all", "D", "R"):
            xs = [i for i in ids if pa == "all" or party[i] == pa]
            if not xs:
                continue
            for k in DIMS:
                vals = [score_of(i, k) for i in xs]
                num = [v for v in vals if v is not None]
                rows.append({"d": day, "c": cong, "p": pa, "k": k, "n": len(xs),
                             "hi": sum(v >= 3 for v in num), "mean": round(sum(num) / len(num), 3) if num else None})
    return rows


def month_ends(start="2023-01", end=SNAPSHOT_DATE):
    y, m = map(int, start.split("-"))
    out = []
    while True:
        nxt = date(y + (m == 12), m % 12 + 1, 1)
        d = nxt - timedelta(days=1)
        if d.isoformat() > end:
            break
        out.append(d.isoformat())
        y, m = nxt.year, nxt.month
    return out + [end]


def backfill():
    roster, groups = cohorts()
    base = json.loads(LABELS_BASE.read_text())
    daily = load_json(LABELS_DAILY, {})
    ev = {p["id"]: json.loads((ROOT / "evidence" / f"{p['id']}.json").read_text())["statements"] for p in roster}
    L = {pid: judge_labels(pid, base, daily) for pid in ev}
    rows = []
    for day in month_ends():
        rf = recent_cutoff(day)
        cache = {}
        for pid, st in ev.items():
            keep = {s["sid"]: s.get("date") for s in st if (s.get("date") or "9999") <= day}
            lab = {j: {sid: v for sid, v in L[pid][j].items() if sid in keep} for j in L[pid]}
            cache[pid] = score_member(lab, keep, len(keep), rf)
        rows += summarize(day, lambda i, k: cache[i][k][0], roster, groups)
        print(day, "done", flush=True)
    save_json(HIST / "backfill.json", rows)


def snapshot():
    roster, groups = cohorts()
    scores = json.loads((ROOT / "data/scores.json").read_text())
    def score_of(i, k):
        v = (scores.get(i) or {}).get("dimensions", {}).get(k, {}).get("score")
        return v if isinstance(v, (int, float)) else None
    save_json(HIST / f"{today()}.json", summarize(today(), score_of, roster, groups))


def build():
    rows = load_json(HIST / "backfill.json", [])
    last = max((r["d"] for r in rows), default="")
    for f in sorted(HIST.glob("20*.json")):
        if f.stem > last:
            rows += json.loads(f.read_text())
    save_json(ROOT / "site/data/history.json", rows)
    print("history rows", len(rows))


if __name__ == "__main__":
    {"backfill": backfill, "snapshot": snapshot, "build": build}[sys.argv[1]]()
