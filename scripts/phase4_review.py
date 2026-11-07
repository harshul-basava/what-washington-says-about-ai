"""Phase 4: build the human review packet + compare with Roe's scores.

Outputs:
  review/review_sheet.csv   one row per (person, dimension) with an empty `your_score` column
  review/review_packet.md   readable packet: summary, scores, justification, cited quotes
  review/roe_comparison.md  rank correlation + biggest disagreements vs Roe (Jan 2026)
"""
import csv
import json
import random
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "review"
OUT.mkdir(exist_ok=True)
DIMS = ["ai_overall", "agi_pilled", "x_risk", "china_race", "regulation"]
ROE = ROOT / "data/raw/roe/politicians_views_ai"
ROE_MAP = {"agi_pilled": "agi_pilled_scores.json", "x_risk": "xrisk_pilled_scores.json", "china_race": "china_focus_scores.json"}


def key(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r'"[^"]*"|\(.*?\)|\b(jr|sr|ii|iii|iv)\b\.?', " ", s)
    t = re.sub(r"[^a-z ]", " ", s).split()
    return (t[0], t[-1]) if t else ("", "")


def spearman(a, b):
    def ranks(x):
        order = sorted(range(len(x)), key=lambda i: x[i])
        r = [0.0] * len(x)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r
    ra, rb = ranks(a), ranks(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = sum((x - ma) ** 2 for x in ra) ** 0.5
    vb = sum((y - mb) ** 2 for y in rb) ** 0.5
    return cov / (va * vb) if va and vb else float("nan")


def main():
    roster = {p["id"]: p for p in json.loads((ROOT / "data/roster.json").read_text())}
    scores = json.loads((ROOT / "data/scores.json").read_text())

    def num(pid, k):
        v = scores.get(pid, {}).get("dimensions", {}).get(k, {}).get("score")
        return v if isinstance(v, (int, float)) else None

    scored = [pid for pid in roster if scores.get(pid, {}).get("summary")]
    def top(k, n):  # top n, extended to include everyone tied with the n-th score
        r = sorted([p for p in scored if num(p, k) is not None], key=lambda p: -num(p, k))
        return [p for p in r if num(p, k) >= num(r[min(n, len(r)) - 1], k)] if r else []
    # highest scorers only (3.5+), so ties at 3 don't flood the packet
    hi = lambda k: sorted([p for p in scored if (num(p, k) or 0) >= 3.5], key=lambda p: -num(p, k))
    top_x, top_a = hi("x_risk"), hi("agi_pilled")
    flagged = [p for p in scored if scores[p].get("flag")]
    rest = [p for p in scored if p not in set(top_x + top_a + flagged)]
    rand = random.Random(42).sample(rest, min(10, len(rest)))
    picks = []
    for why, ids in (("top x-risk", top_x), ("top AGI-pilled", top_a), ("flagged: runs disagreed", flagged), ("random", rand)):
        for pid in ids:
            if pid not in [p for p, _ in picks]:
                picks.append((pid, why))

    md = ["# Review packet", "", f"{len(picks)} people. For each one, check the scores against the quotes. "
          "Enter your own score in `review_sheet.csv` (`your_score`) wherever you disagree. Leave it blank if you agree.", ""]
    rows = []
    for pid, why in picks:
        p, s = roster[pid], scores[pid]
        ev = {x["sid"]: x for x in json.loads((ROOT / "evidence" / f"{pid}.json").read_text())["statements"]}
        md += [f"## {p['name']} ({p['party']}, {p['state']}) — *{why}*", "", s.get("summary") or "", "",
               f"Evidence: {s.get('evidence_strength')} · {len(ev)} statements"
               + (f" · **flag:** {'; '.join(s.get('flag_reasons', []))}" if s.get("flag") else ""), ""]
        for k in DIMS:
            d = s["dimensions"][k]
            md.append(f"- **{k}: {d['score']}** (runs: {d.get('run_a')}/{d.get('run_b')}) — {d.get('justification')}")
            for sid in d.get("statement_ids", [])[:3]:
                q = ev.get(sid)
                if q:
                    md.append(f"    - “{q['text'][:400]}” — {q['source_type']}, {q.get('date')}, {q['url']}")
            rows.append({"id": pid, "name": p["name"], "why": why, "dimension": k, "model_score": d["score"],
                         "run_a": d.get("run_a"), "run_b": d.get("run_b"), "your_score": "", "note": ""})
        md.append("")
    (OUT / "review_packet.md").write_text("\n".join(md))
    with open(OUT / "review_sheet.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # Roe comparison
    by_key = {key(p["name"]): pid for pid, p in roster.items() if p["status"] == "current"}
    out = ["# Comparison with Roe (Jan 2026)", "",
           "Roe's scores run from 0 to 100 (GPT-4o judging Sonnet 4.5's 10-quote research). Ours run from 0 to 4 and are based only on verified quotes. "
           "Spearman ρ is computed over members scored by both.", ""]
    for k, fn in ROE_MAP.items():
        roe = json.loads((ROE / fn).read_text())["scores"]
        pairs = []
        for name, v in roe.items():
            pid = by_key.get(key(name))
            if pid and num(pid, k) is not None:
                pairs.append((pid, v["score"], num(pid, k)))
        if len(pairs) < 5:
            continue
        rho = spearman([x[1] for x in pairs], [x[2] for x in pairs])
        out += [f"## {k}", "", f"n = {len(pairs)} · Spearman ρ = **{rho:.2f}**", "",
                "Biggest disagreements (Roe's percentile vs. ours):", ""]
        rr = sorted(pairs, key=lambda x: x[1])
        ro = sorted(pairs, key=lambda x: x[2])
        pr = {x[0]: i / (len(pairs) - 1) for i, x in enumerate(rr)}
        po = {x[0]: i / (len(pairs) - 1) for i, x in enumerate(ro)}
        for pid, rv, ov in sorted(pairs, key=lambda x: -abs(pr[x[0]] - po[x[0]]))[:10]:
            out.append(f"- {roster[pid]['name']}: Roe {rv:.0f}/100 vs ours {ov}/4")
        out.append("")
    (OUT / "roe_comparison.md").write_text("\n".join(out))
    print(f"review packet: {len(picks)} people; roe comparison written")


if __name__ == "__main__":
    main()
