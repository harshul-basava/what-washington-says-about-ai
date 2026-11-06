"""Phase 5: build site/data/* from roster + evidence + scores."""
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
DATA = SITE / "data"
(DATA / "quotes").mkdir(parents=True, exist_ok=True)
DIMS = ["ai_overall", "agi_pilled", "x_risk", "china_race", "regulation"]


def govtrack_ideology():
    """GovTrack 119th-Congress ideology (0=left, 1=right), keyed by GovTrack ID (copy in Roe's repo)."""
    out = {}
    base = ROOT / "data/raw/roe/politicians_views_ai"
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


def main():
    roster = json.loads((ROOT / "data/roster.json").read_text())
    scores = json.loads((ROOT / "data/scores.json").read_text())
    legis = {m["id"]["bioguide"]: m for m in json.loads((ROOT / "data/raw/legislators-current.json").read_text())}
    gt = govtrack_ideology()
    handles = json.loads((ROOT / "data/handles.json").read_text()) if (ROOT / "data/handles.json").exists() else {}

    members, timeline = [], defaultdict(Counter)
    for p in roster:
        ev = json.loads((ROOT / "evidence" / f"{p['id']}.json").read_text())
        sc = scores.get(p["id"], {})
        topics = sc.get("topics", {})
        gid = legis.get(p["id"], {}).get("id", {}).get("govtrack")
        pl = party_letter(p["party"])
        quotes = []
        for s in ev["statements"]:
            t = topics.get(s["sid"]) or []
            quotes.append({"sid": s["sid"], "text": s["text"], "date": s.get("date"), "src": s["source_type"],
                           "url": s["url"], "topics": t})
            q = quarter(s.get("date"))
            if q and q >= "2023-Q1":
                for tp in (t or ["untagged"]):
                    timeline[(q, pl)][tp] += 1 / max(1, len(t))  # split multi-tag statements evenly
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
            "strength": sc.get("evidence_strength") or "none",
            "summary": sc.get("summary"),
            "flag": sc.get("flag", False),
        })
    (DATA / "members.json").write_text(json.dumps({"updated": date.today().isoformat(), "members": members}))
    tl = [{"q": q, "party": pa, "topic": t, "n": round(n, 2)} for (q, pa), c in sorted(timeline.items()) for t, n in c.items()]
    (DATA / "timeline.json").write_text(json.dumps(tl))
    with open(DATA / "members.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "chamber", "state", "district", "party", "status", "x_handle", "govtrack_ideology",
                    "n_statements", "evidence_strength", *DIMS, "summary"])
        for m in members:
            w.writerow([m["id"], m["name"], m["chamber"], m["state"], m["district"], m["party"], m["status"], m["handle"],
                        m["ideology"], m["n"], m["strength"], *[m["scores"][k] for k in DIMS], m["summary"]])
    print("members", len(members), "timeline rows", len(tl))


if __name__ == "__main__":
    main()
