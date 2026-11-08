"""Phase 5: build site/data/* from roster + evidence + scores."""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from policy_judgments import build as build_policies
SITE = ROOT / "site"
DATA = SITE / "data"
(DATA / "quotes").mkdir(parents=True, exist_ok=True)
DIMS = ["ai_overall", "agi_pilled", "x_risk", "china_race", "regulation"]


def govtrack_ideology():
    """GovTrack 119th-Congress ideology (0=left, 1=right), keyed by GovTrack ID (copy in Roe's repo)."""
    out = {}
    base = ROOT / "data/ref"
    for f in ("sponsorshipanalysis_h.txt", "sponsorshipanalysis_s.txt"):
        with open(base / f) as fh:
            for r in csv.DictReader(fh, skipinitialspace=True):
                out[int(r["ID"])] = round(float(r["ideology"]), 3)
    return out


def party_letter(p):
    p = (p or "").lower()
    return "D" if p.startswith("dem") or p == "dfl" else "R" if p.startswith("rep") else "I"


def quarter(d):
    m = re.match(r"(\d{4})-(\d{2})", d or "")
    if not m:
        return None
    return f"{m.group(1)}-Q{(int(m.group(2)) - 1) // 3 + 1}"


TOPICS = ["jobs/economy", "China/competition", "national security", "kids/online safety", "deepfakes/elections",
          "copyright", "energy/data centers", "regulation", "AGI/transformative", "x-risk/loss of control",
          "misuse (bio/cyber)", "other"]
_TKEY = {re.sub(r"[^a-z]", "", t.lower()): t for t in TOPICS}
_TKEY.update({"misuse": "misuse (bio/cyber)", "xrisk": "x-risk/loss of control", "agi": "AGI/transformative"})


def canon_topic(t):
    """Map the scorer's off-list topic variants ('energy data centers', 'misuse') onto the fixed list."""
    return _TKEY.get(re.sub(r"[^a-z]", "", str(t).lower()), "other")


# AI-relevant full committees (thomas_id -> short label), for the committee view
COMMITTEES = {
    "SSCM": "Senate Commerce", "SSJU": "Senate Judiciary", "SSAS": "Senate Armed Services", "SLIN": "Senate Intelligence",
    "SSHR": "Senate HELP", "SSGA": "Senate Homeland Security",
    "HSIF": "House Energy & Commerce", "HSSY": "House Science", "HSJU": "House Judiciary",
    "HSZS": "House Select Cmte on China", "HSAS": "House Armed Services", "HLIG": "House Intelligence",
}


def committee_roles():
    mem = json.loads((ROOT / "data/ref/committee-membership-current.json").read_text())
    out = defaultdict(list)
    for cid in COMMITTEES:
        for r in mem.get(cid, []):
            out[r["bioguide"]].append({"c": cid, "title": r.get("title"), "side": r.get("party")})
    return out


def main():
    roster = json.loads((ROOT / "data/roster.json").read_text())
    scores = json.loads((ROOT / "data/scores.json").read_text())
    legis = {m["id"]["bioguide"]: m for m in json.loads((ROOT / "data/ref/legislators-current.json").read_text())}
    gt = govtrack_ideology()
    nxt_f = ROOT / "data/next_congress.json"
    nxt = json.loads(nxt_f.read_text()) if nxt_f.exists() else {}
    roles = committee_roles()
    lab_f = ROOT / "data/labels.json"
    LABELS = json.loads(lab_f.read_text()) if lab_f.exists() else {}
    daily_f = ROOT / "data/labels_daily.json"
    DAILY = json.loads(daily_f.read_text()) if daily_f.exists() else {}   # statements added by the daily job (cascade)
    handles = json.loads((ROOT / "data/handles.json").read_text()) if (ROOT / "data/handles.json").exists() else {}

    members, timeline, byday = [], defaultdict(Counter), defaultdict(Counter)
    for p in roster:
        ev = json.loads((ROOT / "evidence" / f"{p['id']}.json").read_text())
        sc = scores.get(p["id"], {})
        topics = sc.get("topics", {})
        gid = legis.get(p["id"], {}).get("id", {}).get("govtrack")
        pl = party_letter(p["party"])
        quotes = []
        group = (nxt.get(p["id"]) or {}).get("status", "continuing")
        mtopics = Counter()
        for s in ev["statements"]:
            t = list(dict.fromkeys(canon_topic(x) for x in (topics.get(s["sid"]) or [])))
            lab = (LABELS.get(p["id"]) or {}).get(s["sid"]) or {}
            by = ["Claude", "GPT"]
            dl = (DAILY.get(p["id"]) or {}).get(s["sid"])
            if dl:
                lab, by = {"sonnet": dl.get("a") or {}, "gpt": dl.get("b") or {}}, [dl["models"]["a"], dl["models"]["b"]]
            quotes.append({"sid": s["sid"], "text": s["text"], "date": s.get("date"), "src": s["source_type"],
                           "url": s["url"], "topics": t, "by": by, "added": s.get("added"),
                           "lab": {k: [lab.get("sonnet", {}).get(k), lab.get("gpt", {}).get(k)] for k in DIMS
                                   if lab.get("sonnet", {}).get(k) is not None or lab.get("gpt", {}).get(k) is not None}})
            d = (s.get("date") or "")[:10]
            if len(d) == 10 and d >= "2023-01-01":
                for tp in (t or ["untagged"]):
                    byday[(d, pl, group)][tp] += 1 / max(1, len(t))
            q = quarter(s.get("date"))
            if q and q >= "2023-Q1":
                for tp in (t or ["untagged"]):
                    timeline[(q, pl, group)][tp] += 1 / max(1, len(t))
            for tp in (t or ["untagged"]):
                mtopics[tp] += 1 / max(1, len(t))  # split multi-tag statements evenly
        cited = {k: (sc.get("dimensions", {}).get(k, {}).get("statement_ids") or []) for k in DIMS}
        (DATA / "quotes" / f"{p['id']}.json").write_text(json.dumps({"quotes": quotes, "cited": cited}))
        dims = sc.get("dimensions", {})
        members.append({
            "id": p["id"], "name": p["name"], "chamber": p["chamber"], "state": p["state"],
            "district": p["district"], "party": pl, "status": p["status"],
            "ideology": gt.get(gid) if gid else None,
            "handle": handles.get(p["id"]),
            "n": len(quotes),
            "n_by_src": dict(Counter(q["src"] for q in quotes)),
            "scores": {k: (dims.get(k, {}).get("score") if isinstance(dims.get(k, {}).get("score"), (int, float)) else None) for k in DIMS},
            "just": {k: dims.get(k, {}).get("justification") for k in DIMS},
            "reason": {k: [dims.get(k, {}).get("reason_a"), dims.get(k, {}).get("reason_b")] for k in DIMS},
            "strength": sc.get("evidence_strength") or "none",
            "summary": sc.get("summary"),
            "flag": sc.get("flag", False),
            "reviewed": bool(sc.get("human_reviewed")),
            "next": group,
            "next_chamber": (nxt.get(p["id"]) or {}).get("chamber", p["chamber"]),
            "committees": roles.get(p["id"], []),
            "topics": {k: round(v, 2) for k, v in mtopics.items()},
        })
    (DATA / "members.json").write_text(json.dumps({"updated": date.today().isoformat(), "members": members}))
    tl = [{"q": q, "party": pa, "g": g, "topic": t, "n": round(n, 2)} for (q, pa, g), c in sorted(timeline.items()) for t, n in c.items()]
    (DATA / "committees.json").write_text(json.dumps(COMMITTEES))
    (DATA / "timeline.json").write_text(json.dumps(tl))
    with open(DATA / "members.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "chamber", "state", "district", "party", "status", "next_congress", "x_handle", "govtrack_ideology",
                    "n_statements", "evidence_strength", *DIMS, "summary"])
        for m in members:
            w.writerow([m["id"], m["name"], m["chamber"], m["state"], m["district"], m["party"], m["status"], m["next"], m["handle"],
                        m["ideology"], m["n"], m["strength"], *[m["scores"][k] for k in DIMS], m["summary"]])
    # daily topic counts (the site computes rolling shares from these)
    tidx = {t: i for i, t in enumerate(TOPICS + ["untagged"])}
    rows = [[d, pa, g, tidx.get(tp, tidx["other"]), round(n, 2)] for (d, pa, g), c in sorted(byday.items()) for tp, n in c.items()]
    (DATA / "daily.json").write_text(json.dumps({"topics": TOPICS + ["untagged"], "rows": rows}))
    # recent big score changes from the daily job
    ch_f = ROOT / "data/changes.jsonl"
    changes = [json.loads(x) for x in ch_f.read_text().splitlines()] if ch_f.exists() else []
    cutoff = (date.today() - timedelta(days=60)).isoformat()
    (DATA / "changes.json").write_text(json.dumps([c for c in changes if c["kind"] == "big" and c["date"] >= cutoff][::-1][:100]))
    # which kinds of AI rules each member supports or opposes (phase6_reg_focus.py)
    rf_f = ROOT / "data/reg_focus.json"
    if rf_f.exists():
        rubric = (ROOT / "config/reg_focus.md").read_text()
        rows_rf = re.findall(r"^\| `([a-z_]+)` \| ([^|]+?) \| ([^|]+?) \| ([^|]+?) \|", rubric, re.M)
        areas = [[a, n.strip(), "harms" if i < 10 else "frontier", sup.strip(), opp.strip()] for i, (a, n, sup, opp) in enumerate(rows_rf)]
        rf = json.loads(rf_f.read_text())
        (DATA / "regfocus.json").write_text(json.dumps({"areas": areas, "labeled": len(rf),
                                                        "m": {pid: r["final"] for pid, r in rf.items() if r.get("final")}}))
    print("members", len(members), "timeline rows", len(tl), "daily rows", len(rows))
    # The daily job invokes this entry point directly, bypassing Makefile targets.
    # Rebuild from saved judgments only; new or changed evidence stays pending.
    policies = build_policies(ROOT)
    print("policies", len(policies["policies"]))


if __name__ == "__main__":
    main()
