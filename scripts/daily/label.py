"""Cascade labeling for statements added by the daily job.

1. DeepSeek labels each new statement 3 times (temperature 0.7), with a confidence (1-5) per label and topic tags.
2. A (statement, question) label is escalated when the 3 runs disagree, the mean confidence is below
   CONF_MIN, it claims a high level on x-risk or AGI (3+), or it is 2+ away from the member's current score.
3. GPT-6.1 Sol labels the escalated statements on its own (it does not see DeepSeek's labels).
4. GPT-6 Astra breaks ties when Sol and DeepSeek are 2+ levels apart.

Result per statement in data/labels_daily.json:
  {"a": {...}, "b": {...}, "ds": [run1, run2, run3], "conf": {...}, "esc": [...], "sol": {...}|null,
   "astra": {...}|null, "topics": [...], "models": {"a": ..., "b": ...}, "labeled": "YYYY-MM-DD"}
Slots a and b feed the same two-judge formula as the original Sonnet/GPT labels (phase3_label.judge_labels).

Usage: python scripts/daily/label.py [--ids A,B] [--dry-run]
"""
import argparse
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from common import ROOT, load_json, save_json, today
import llm
from phase3_label import DIMS, LABELS_DAILY, PROMPT, RUBRIC, parse as parse_plain

DS = "deepseek/deepseek-v4.1-flash"
SOL = "openai/gpt-6.1-sol"
ASTRA = "openai/gpt-6-astra"
NAMES = {DS: "DeepSeek V4.1 Flash", SOL: "GPT-6.1 Sol", ASTRA: "GPT-6 Astra"}
RUNS = 3
WORKERS = 6              # members labeled at the same time
CONF_MIN = 3.0            # set from review/cascade_calibration.md (2026-11-07)
HIGH_STAKES = {"x_risk": 3, "agi_pilled": 3}
TOPICS = ["jobs/economy", "China/competition", "national security", "kids/online safety", "deepfakes/elections",
          "copyright", "energy/data centers", "regulation", "AGI/transformative", "x-risk/loss of control",
          "misuse (bio/cyber)", "other"]
CASCADE_NOTE = """

## Output for this pass
For each label, also give your confidence that the level is right, from 1 (a guess) to 5 (certain), as [level, confidence].
Also tag every statement with 1-3 topics from this list: {topics}.
Return only a JSON object:
```json
{{"labels": {{"s12": {{"x_risk": [3, 4], "regulation": [3, 5]}}}}, "topics": {{"s12": ["x-risk/loss of control", "regulation"]}}}}
```"""


def build(name, stmts, note=""):
    lines = [f"[{s['sid']}] ({s.get('date') or 'undated'}; {s['source_type']}) {' '.join(s['text'].split())[:900]}" for s in stmts]
    return PROMPT.format(rubric=RUBRIC, name=name, statements="\n".join(lines)) + note


def parse_cascade(text, sids):
    """-> (labels {sid: {dim: level}}, conf {sid: {dim: c}}, topics {sid: [..]}) or None."""
    m = re.search(r"\{[\s\S]*\}", text or "")
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None
    labels, conf = {}, {}
    for sid, dims in (d.get("labels") or {}).items():
        if sid not in sids or not isinstance(dims, dict):
            continue
        for k, v in dims.items():
            lv, c = (v[0], v[1] if len(v) > 1 else 3) if isinstance(v, list) and v else (v, 3)
            if k in DIMS and isinstance(lv, (int, float)) and 0 <= lv <= 4:
                labels.setdefault(sid, {})[k] = int(lv)
                conf.setdefault(sid, {})[k] = float(c) if isinstance(c, (int, float)) else 3.0
    topics = {sid: [t for t in ts if t in TOPICS][:3] for sid, ts in (d.get("topics") or {}).items() if sid in sids and isinstance(ts, list)}
    return labels, conf, topics


REASONING = {DS: {"effort": "low"}}   # DeepSeek V4.1 Flash otherwise spends its whole output budget on reasoning


def call(model, prompt, tag, temperature=None):
    extra = {"temperature": temperature} if temperature is not None else {}
    if model in REASONING:
        extra["reasoning"] = REASONING[model]
    d = llm.chat([{"role": "user", "content": prompt}], tag=tag, model=model, max_tokens=24000 if model in REASONING else 8000, **extra)
    return d["choices"][0]["message"]["content"]


def chunks(xs, n=40):
    return [xs[i:i + n] for i in range(0, len(xs), n)]


def deepseek_runs(name, stmts, tag="daily_label_ds"):
    sids = {s["sid"] for s in stmts}
    runs = []
    for r in range(RUNS):
        res = None
        for attempt in range(2):
            res = parse_cascade(call(DS, build(name, stmts, CASCADE_NOTE.format(topics=", ".join(TOPICS))), tag, 0.7), sids)
            if res is not None:
                break
        runs.append(res or ({}, {}, {}))
    return runs


def independent(model, name, stmts, tag):
    out = {}
    for part in chunks(stmts):
        lab = parse_plain(call(model, build(name, part), tag), {s["sid"] for s in part})
        out.update(lab or {})
    return out


def decide(sid, runs, current):
    """Majority label per question, confidence, and which questions escalate."""
    maj, conf, esc = {}, {}, []
    for k in DIMS:
        vals = [r[0].get(sid, {}).get(k) for r in runs]
        top, n = Counter(vals).most_common(1)[0]
        cs = [r[1].get(sid, {}).get(k) for r in runs if r[0].get(sid, {}).get(k) is not None]
        c = sum(cs) / len(cs) if cs else None
        if top is not None:
            maj[k] = top
            conf[k] = round(c, 2) if c is not None else None
        labeled_any = any(v is not None for v in vals)
        if not labeled_any:
            continue
        unanimous = n == len(vals)
        low_conf = c is not None and c < CONF_MIN
        stakes = top is not None and top >= HIGH_STAKES.get(k, 9)
        far = top is not None and isinstance(current.get(k), (int, float)) and abs(top - current[k]) >= 2
        if not unanimous or low_conf or stakes or far:
            esc.append(k)
    return maj, conf, esc


def label_member(pid, sids, scores, dry=False):
    ev = json.loads((ROOT / "evidence" / f"{pid}.json").read_text())
    stmts = [s for s in ev["statements"] if s["sid"] in sids]
    if not stmts or dry:
        return {}
    name = ev["name"]
    current = {k: (scores.get(pid, {}).get("dimensions", {}).get(k, {}).get("score")) for k in DIMS}
    runs = []
    per_part = [deepseek_runs(name, part) for part in chunks(stmts)]
    for i in range(RUNS):   # merge the parts of each run
        lab, conf, top = {}, {}, {}
        for pr in per_part:
            lab.update(pr[i][0]); conf.update(pr[i][1]); top.update(pr[i][2])
        runs.append((lab, conf, top))
    decided = {s["sid"]: decide(s["sid"], runs, current) for s in stmts}
    to_review = [s for s in stmts if decided[s["sid"]][2]]
    sol = independent(SOL, name, to_review, "daily_label_sol") if to_review else {}
    def apart(sid, k):   # Sol and DeepSeek both labeled this question, 2+ levels apart
        x, y = (sol.get(sid) or {}).get(k), decided[sid][0].get(k)
        return x is not None and y is not None and abs(x - y) >= 2
    tie = [s for s in to_review if any(apart(s["sid"], k) for k in decided[s["sid"]][2])]
    astra = independent(ASTRA, name, tie, "daily_label_astra") if tie else {}
    out = {}
    for s in stmts:
        sid = s["sid"]
        maj, conf, esc = decided[sid]
        a, b = dict(maj), dict(maj)
        tie_ids = {x["sid"] for x in tie}
        for k in esc:
            sv = (sol.get(sid) or {}).get(k)
            b.pop(k, None)
            if sv is not None:
                b[k] = sv
            av = (astra.get(sid) or {}).get(k) if sid in tie_ids else None
            if av is not None and k in a and k in b:   # Astra replaces whichever label is farther from it
                if abs(av - a[k]) > abs(av - b[k]):
                    a[k] = av
                else:
                    b[k] = av
        topics = Counter(t for r in runs for t in r[2].get(sid, []))
        out[sid] = {"a": a, "b": b, "ds": [r[0].get(sid, {}) for r in runs], "conf": conf, "esc": esc,
                    "sol": sol.get(sid) if sid in {x["sid"] for x in to_review} else None,
                    "astra": astra.get(sid) if sid in {x["sid"] for x in tie} else None,
                    "topics": [t for t, n in topics.most_common(3) if n >= 2] or [t for t, _ in topics.most_common(1)],
                    "models": {"a": NAMES[DS], "b": NAMES[SOL] if esc else NAMES[DS]}, "labeled": today()}
    return out


def pending():
    """{pid: [sids]} for statements added by the daily job that have no daily label yet."""
    done = load_json(LABELS_DAILY, {})
    out = {}
    log = ROOT / "data/new_statements.jsonl"
    if not log.exists():
        return out
    for line in log.read_text().splitlines():
        r = json.loads(line)
        if r["sid"] not in (done.get(r["id"]) or {}):
            out.setdefault(r["id"], []).append(r["sid"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    todo = pending()
    if a.ids:
        todo = {k: v for k, v in todo.items() if k in set(a.ids.split(","))}
    scores = load_json(ROOT / "data/scores.json", {})
    done = load_json(LABELS_DAILY, {})
    stats = Counter()
    if a.dry_run:
        stats["statements"] = sum(len(v) for v in todo.values())
    else:
        def work(item):
            pid, sids = item
            try:
                return pid, label_member(pid, set(sids), scores), None
            except llm.BudgetExceeded as e:
                return pid, {}, f"budget: {e}"
            except Exception as e:  # noqa: BLE001  one member failing must not stop the others; it stays pending
                return pid, {}, f"error: {str(e)[:200]}"
        with ThreadPoolExecutor(WORKERS) as ex:
            for pid, res, err in ex.map(work, todo.items()):
                if err:
                    print(pid, err)
                    stats["budget_stop" if err.startswith("budget") else "errors"] += 1
                    continue
                done.setdefault(pid, {}).update(res)
                save_json(LABELS_DAILY, done)   # save after each member, so a crash loses little
                stats["members"] += 1
                stats["statements"] += len(res)
                stats["escalated"] += sum(bool(r["esc"]) for r in res.values())
                stats["astra"] += sum(r["astra"] is not None for r in res.values())
    print(json.dumps(dict(stats)))
    return {"labeled": {pid: sids for pid, sids in todo.items()}, "stats": dict(stats)}


if __name__ == "__main__":
    main()
