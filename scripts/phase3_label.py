"""Phase 3 (rubric v3): label every statement with two judge models, then score with a fixed formula.

  python scripts/phase3_label.py sync --ids A,B [--judges sonnet,gpt]   # regular calls (pilot)
  python scripts/phase3_label.py submit [--judges sonnet,gpt]           # OpenRouter batch
  python scripts/phase3_label.py collect                                # poll batches, then fill gaps with regular calls
  python scripts/phase3_label.py combine                                # data/scores.json + data/labels.json
  python scripts/phase3_label.py report                                 # review/judge_agreement.md

Each judge labels statements (not people), in chunks of CHUNK statements. The score for a question comes
from the labels via the formula in config/rubric.md; the published score is the mean of the two judges.
Summaries and topic tags are carried over from the v2 scoring run (same evidence).
"""
import json
import re
import statistics
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import llm  # noqa: E402

DIMS = ["ai_overall", "agi_pilled", "x_risk", "china_race", "regulation"]
INTENSITY = {"x_risk", "agi_pilled", "china_race"}
JUDGES = {"sonnet": "anthropic/claude-sonnet-5.5", "gpt": "openai/gpt-6.1-sol"}
RUBRIC_TXT = (ROOT / "config/rubric.md").read_text()
RUBRIC_VERSION = re.search(r"rubric (v\d+)", RUBRIC_TXT).group(1)
RUBRIC = RUBRIC_TXT.split("-->", 1)[1].strip()
PROMPT = (ROOT / "config/label_prompt.md").read_text().split("-->", 1)[1].strip()
OUT = ROOT / "data/raw/labels"
BATCHES = ROOT / "data/raw/label_batches.json"
BATCH_URL = "https://openrouter.ai/api/v1/batches"
CHUNK = 80
MAX_CHARS = 900
DATA_DATE = date(2026, 11, 5)
RECENT = (DATA_DATE - timedelta(days=730)).isoformat()
HEAD = {"Authorization": f"Bearer {llm.os.environ['OPENROUTER_API_KEY']}"}


def people():
    out = []
    for p in json.loads((ROOT / "data/roster.json").read_text()):
        ev = json.loads((ROOT / "evidence" / f"{p['id']}.json").read_text())
        if ev["statements"]:
            out.append(ev)
    return out


def chunks(ev):
    st = sorted(ev["statements"], key=lambda s: int(s["sid"][1:]))
    return [st[i:i + CHUNK] for i in range(0, len(st), CHUNK)]


def build(ev, part):
    lines = [f"[{s['sid']}] ({s.get('date') or 'undated'}; {s['source_type']}) {' '.join(s['text'].split())[:MAX_CHARS]}" for s in part]
    return PROMPT.format(rubric=RUBRIC, name=ev["name"], statements="\n".join(lines))


def parse(text, valid_sids):
    m = re.search(r"\{[\s\S]*\}", text or "")
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None
    labels = {}
    for sid, dims in (d.get("labels") or {}).items():
        if sid not in valid_sids or not isinstance(dims, dict):
            continue
        clean = {k: int(v) for k, v in dims.items() if k in DIMS and isinstance(v, (int, float)) and 0 <= v <= 4}
        if clean:
            labels[sid] = clean
    return labels


def path(judge, pid, i):
    return OUT / judge / f"{pid}__{i}.json"


def todo(judges):
    for ev in people():
        for i, part in enumerate(chunks(ev)):
            for j in judges:
                if not path(j, ev["id"], i).exists():
                    yield ev, i, part, j


def sync(ids, judges):
    for ev, i, part, j in [t for t in todo(judges) if t[0]["id"] in ids]:
        d = llm.chat([{"role": "user", "content": build(ev, part)}], tag=f"phase3v3_sync_{j}", model=JUDGES[j], max_tokens=8000)
        res = parse(d["choices"][0]["message"]["content"], {s["sid"] for s in part})
        if res is None:
            print(ev["name"], i, j, "PARSE FAIL")
            continue
        path(j, ev["id"], i).parent.mkdir(parents=True, exist_ok=True)
        path(j, ev["id"], i).write_text(json.dumps(res))
        print(f"{ev['name']} chunk {i} {j}: {len(res)} labeled of {len(part)} · ${d['usage']['cost']:.3f}", flush=True)


def submit(judges, size=150):
    items = list(todo(judges))
    est = sum(len(build(ev, part)) / 3.5 / 1e6 * 1.0 + 1500 / 1e6 * 5.0 for ev, _, part, _ in items)
    left = llm.BUDGETS["openrouter"] - llm.spent("openrouter")
    print(f"{len(items)} requests, est ${est:.2f}, budget left ${left:.2f}")
    if est > left:
        raise SystemExit("would exceed budget")
    batches = json.loads(BATCHES.read_text()) if BATCHES.exists() else []
    for j in judges:
        mine = [t for t in items if t[3] == j]
        for k in range(0, len(mine), size):
            part = mine[k:k + size]
            body = {"endpoint": "/v1/chat/completions", "model": JUDGES[j], "completion_window": "24h", "requests": [
                {"custom_id": f"{ev['id']}__{i}__{j}",
                 "body": {"messages": [{"role": "user", "content": build(ev, ch)}], "max_tokens": 8000}}
                for ev, i, ch, _ in part]}
            r = httpx.post(BATCH_URL, json=body, headers=HEAD, timeout=300)
            if r.status_code not in (200, 201, 202):
                raise SystemExit(f"batch submit failed {r.status_code}: {r.text[:500]}")
            batches.append({"id": r.json()["id"], "judge": j, "n": len(part), "logged": False})
            BATCHES.write_text(json.dumps(batches, indent=1))
            print("submitted", j, batches[-1]["id"], len(part), flush=True)


def collect():
    evs = {ev["id"]: ev for ev in people()}
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
                pid, i, j = res["custom_id"].rsplit("__", 2)
                if res.get("response") and res["response"].get("status_code") == 200:
                    part = chunks(evs[pid])[int(i)]
                    lab = parse(res["response"]["body"]["choices"][0]["message"]["content"], {s["sid"] for s in part})
                    if lab is not None:
                        path(j, pid, i).parent.mkdir(parents=True, exist_ok=True)
                        path(j, pid, i).write_text(json.dumps(lab))
            cost = float((d.get("usage") or {}).get("cost") or 0)
            if not b["logged"]:
                llm._log("openrouter", cost, f"phase3v3_batch_{b['judge']}", {"batch_id": b["id"], "status": st})
                b["logged"] = True
            print(b["id"], b["judge"], st, d.get("request_counts"), f"${cost:.2f}", flush=True)
        BATCHES.write_text(json.dumps(batches, indent=1))
        if not pending:
            break
        time.sleep(60)
    missing = list(todo(list(JUDGES)))
    print(f"{len(missing)} chunks missing after batch; running them as regular calls", flush=True)
    sync({ev["id"] for ev, *_ in missing}, list(JUDGES))


def load_labels(judge, ev):
    lab = {}
    for i in range(len(chunks(ev))):
        f = path(judge, ev["id"], i)
        if f.exists():
            lab.update(json.loads(f.read_text()))
    return lab


def score_one(levels_by_sid, dates, k):
    """Fixed formula from config/rubric.md. Returns (score or None, reason, sids at the deciding level)."""
    lv = [(sid, d[k]) for sid, d in levels_by_sid.items() if k in d]
    recent = [(s, v) for s, v in lv if (dates.get(s) or "") >= RECENT]
    if len(recent) >= 3:
        lv = recent
    if not lv:
        return (0, "silent", []) if k in INTENSITY else (None, "no_statements", [])
    vals = sorted((v for _, v in lv), reverse=True)
    if k in INTENSITY:
        top = vals[0]
        if vals.count(top) >= 2 or vals.count(top) * 3 >= len(vals):
            sc, why = top, "consistent"
        else:
            sc, why = max(top - 1, 0), "one_off_capped" if top > 0 else "dismissive"
        if sc == 0 and why == "consistent":
            why = "dismissive"
        cite_levels = {top} if why == "one_off_capped" else {sc}
    else:
        med = statistics.median(vals)
        sc = int(med) if med == int(med) else (int(med) + 1 if med < 2 else int(med))  # halves round toward 2
        why = f"median_of_{len(vals)}"
        cite_levels = {sc}
    cites = [s for s, v in sorted(lv, key=lambda x: dates.get(x[0]) or "", reverse=True) if v in cite_levels][:6]
    return sc, why, cites


LEVEL_TEXT = {
    "x_risk": ["rejects catastrophic AI risk", "raises catastrophic risk but plays it down", "affirms catastrophic risk is real",
               "calls for action because of catastrophic risk", "ranks catastrophic AI risk among the top problems"],
    "agi_pilled": ["rejects transformative AI or AGI claims", "treats AI as an ordinary technology", "expects very large change from AI",
                   "treats AGI as a real possibility", "says AGI is near or a turning point"],
    "china_race": ["rejects race framing", "mentions the competition without using it", "uses the competition as one reason among several",
                   "uses the competition as the main reason", "argues the competition outweighs other concerns"],
    "ai_overall": ["presents AI as mainly a threat", "treats harms as dominant", "weighs benefits and risks equally",
                   "presents AI as mainly an opportunity", "is enthusiastic about AI"],
    "regulation": ["opposes regulating AI", "prefers light-touch rules", "supports narrow, targeted rules",
                   "supports substantial obligations on AI companies", "supports comprehensive regulation"],
}
WHY_TEXT = {"silent": "No statement addresses this, so it scores 0 (doesn't discuss it).",
            "dismissive": "Their statements on this reject the claim.",
            "consistent": "At least two statements reach this level.",
            "one_off_capped": "Only one statement reaches the highest level, so the score is one step lower.",
            "no_statements": "No statement addresses this."}


def combine():
    evs = people()
    v2 = json.loads((ROOT / "data/raw/v2/scores.json").read_text())
    out, all_labels = {}, {}
    for p in json.loads((ROOT / "data/roster.json").read_text()):
        pid = p["id"]
        ev = next((e for e in evs if e["id"] == pid), None)
        base = v2.get(pid, {})
        if ev is None or len(ev["statements"]) < 3:
            out[pid] = {"dimensions": {k: {"score": "insufficient_evidence", "reason": "too_few_statements"} for k in DIMS},
                        "summary": base.get("summary"), "evidence_strength": base.get("evidence_strength") or "none",
                        "topics": base.get("topics", {}), "flag": False, "rubric_version": RUBRIC_VERSION}
            continue
        dates = {s["sid"]: s.get("date") for s in ev["statements"]}
        L = {j: load_labels(j, ev) for j in JUDGES}
        all_labels[pid] = {sid: {j: L[j].get(sid, {}) for j in JUDGES} for sid in set(L["sonnet"]) | set(L["gpt"])}
        dims, flag, why = {}, False, []
        for k in DIMS:
            res = {j: score_one(L[j], dates, k) for j in JUDGES}
            nums = [r[0] for r in res.values() if r[0] is not None]
            score = sum(nums) / len(nums) if nums else "insufficient_evidence"
            if len(nums) == 2 and abs(nums[0] - nums[1]) >= 2:
                flag, _ = True, why.append(f"{k}: sonnet {nums[0]} vs gpt {nums[1]}")
            a, b = res["sonnet"], res["gpt"]
            def say(r):
                return "not enough evidence" if r[0] is None else f"{r[0]} ({LEVEL_TEXT[k][r[0]]}). {WHY_TEXT.get(r[1], 'Median of ' + r[1].split('_')[-1] + ' labeled statements.')}"
            just = f"Claude: {say(a)} GPT: {say(b)}"
            cites = list(dict.fromkeys(a[2] + b[2]))[:6]
            dims[k] = {"score": score, "run_a": a[0] if a[0] is not None else "insufficient_evidence",
                       "run_b": b[0] if b[0] is not None else "insufficient_evidence",
                       "reason_a": a[1], "reason_b": b[1], "justification": just, "statement_ids": cites}
        out[pid] = {"dimensions": dims, "summary": base.get("summary"), "evidence_strength": base.get("evidence_strength"),
                    "topics": base.get("topics", {}), "flag": flag, "flag_reasons": why, "rubric_version": RUBRIC_VERSION}
    # human review decisions (scripts/phase4_apply_review.py) override the score
    hr_f = ROOT / "data/human_review.json"
    for key, d in (json.loads(hr_f.read_text()) if hr_f.exists() else {}).items():
        pid, k = key.split("|")
        if pid in out and k in out[pid]["dimensions"] and d.get("verdict") in ("agree", "change"):
            dim = out[pid]["dimensions"][k]
            dim["human"] = {"verdict": d["verdict"], "score": d.get("score"), "note": d.get("note", ""), "model_score": dim["score"]}
            if d["verdict"] == "change":
                dim["score"] = d["score"]
            out[pid]["human_reviewed"] = True
    (ROOT / "data/scores.json").write_text(json.dumps(out, indent=1))
    (ROOT / "data/labels.json").write_text(json.dumps(all_labels))
    print("scored", sum(1 for v in out.values() if "run_a" in v["dimensions"]["x_risk"]), "flagged (judges 2+ apart)",
          sum(v["flag"] for v in out.values()))


def report():
    labels = json.loads((ROOT / "data/labels.json").read_text())
    scores = json.loads((ROOT / "data/scores.json").read_text())
    lines = ["# Agreement between the two judges (rubric v3)", "",
             "Claude Sonnet 5.5 and GPT-6.1 Sol each labeled every statement on their own. The published score is the mean of their two scores.", "",
             "## Statement labels", "", "| question | labeled by both | same level | within 1 | labeled by only one |", "|---|---|---|---|---|"]
    for k in DIMS:
        both = same = near = one = 0
        for sids in labels.values():
            for d in sids.values():
                a, b = d["sonnet"].get(k), d["gpt"].get(k)
                if a is not None and b is not None:
                    both += 1; same += a == b; near += abs(a - b) <= 1
                elif a is not None or b is not None:
                    one += 1
        lines.append(f"| {k} | {both} | {same / max(both, 1):.0%} | {near / max(both, 1):.0%} | {one} |")
    lines += ["", "## Member scores", "", "| question | scored by both | same score | within 1 | 2+ apart |", "|---|---|---|---|---|"]
    for k in DIMS:
        pr = [(v["dimensions"][k]["run_a"], v["dimensions"][k]["run_b"]) for v in scores.values() if "run_a" in v["dimensions"][k]]
        pr = [(a, b) for a, b in pr if isinstance(a, int) and isinstance(b, int)]
        n = max(len(pr), 1)
        lines.append(f"| {k} | {len(pr)} | {sum(a == b for a, b in pr) / n:.0%} | {sum(abs(a - b) <= 1 for a, b in pr) / n:.0%} | {sum(abs(a - b) >= 2 for a, b in pr)} |")
    (ROOT / "review/judge_agreement.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    cmd = sys.argv[1]
    judges = sys.argv[sys.argv.index("--judges") + 1].split(",") if "--judges" in sys.argv else list(JUDGES)
    if cmd == "sync":
        sync(set(sys.argv[sys.argv.index("--ids") + 1].split(",")), judges)
    elif cmd == "submit":
        submit(judges)
    else:
        {"collect": collect, "combine": combine, "report": report}[cmd]()
