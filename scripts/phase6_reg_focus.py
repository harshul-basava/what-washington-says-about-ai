"""Phase 6: which kinds of AI rules each member supports or opposes (rubric: config/reg_focus.md).

Two judges read all of a member's verified statements and give a stance per focus area
(2 explicit support, 1 implied support, -1 implied opposition, -2 explicit opposition, omitted = no stance):
  A = DeepSeek V4.1 Flash, B = GPT-6.1 Sol.
Final stance per area:
  - same direction (both support, both oppose, both silent): keep it, at the weaker of the two strengths;
  - different direction: GPT-6 Astra decides, reading only the statements that either judge cited.

Writes data/reg_focus.json: {pid: {"a", "b", "astra", "final": {area: [stance, [sids], reason]}, "models", "labeled", "n"}}.

Usage: python scripts/phase6_reg_focus.py [--ids A,B] [--limit N] [--redo] [--workers 8] [--dry-run]
"""
import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import llm  # noqa: E402

OUT = ROOT / "data/reg_focus.json"
RUBRIC = (ROOT / "config/reg_focus.md").read_text()
AREAS = re.findall(r"^\| `([a-z_]+)` \| ([^|]+?) \|", RUBRIC, re.M)   # [(id, name)] in rubric order
AREA_IDS = [a for a, _ in AREAS]
_FRONTIER = RUBRIC.index("### Catastrophic")
GROUP = {a: ("frontier" if RUBRIC.index(f"| `{a}` |") > _FRONTIER else "harms") for a in AREA_IDS}
DS, SOL, ASTRA = "deepseek/deepseek-v4.1-flash", "openai/gpt-6.1-sol", "openai/gpt-6-astra"
NAMES = {DS: "DeepSeek V4.1 Flash", SOL: "GPT-6.1 Sol", ASTRA: "GPT-6 Astra"}
MAX_CHARS = 1200

PROMPT = """You are labeling a study of what members of Congress say about AI. Apply the rubric below exactly.

{rubric}

## Member: {name}
Each line is: [id] (date; source type) text

{statements}

## Output
{scope}Return only a JSON object with an entry for each area where the member has a stance (omit areas with no stance):
```json
{{"stances": {{"deepfakes": {{"stance": 2, "sids": ["s4", "s19"], "why": "Cosponsored the TAKE IT DOWN Act."}}}}}}
```
Valid areas: {areas}. Valid stances: 2, 1, -1, -2. If the member has no stance on any area, return {{"stances": {{}}}}."""


def stmt_lines(stmts):
    return "\n".join(f"[{s['sid']}] ({s.get('date') or 'undated'}; {s['source_type']}) {' '.join(s['text'].split())[:MAX_CHARS]}"
                     for s in stmts)


def parse(text, sids, allowed=None):
    m = re.search(r"\{[\s\S]*\}", text or "")
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None
    out = {}
    for a, v in (d.get("stances") or {}).items():
        if a not in AREA_IDS or (allowed and a not in allowed) or not isinstance(v, dict):
            continue
        st, cs = v.get("stance"), [s for s in (v.get("sids") or []) if s in sids][:3]
        if st in (2, 1, -1, -2) and cs:   # a stance needs at least one real statement behind it
            out[a] = {"stance": st, "sids": cs, "why": str(v.get("why") or "")[:300]}
    return out


def ask(model, name, stmts, tag, allowed=None):
    scope = (f"Judge only these areas: {', '.join(allowed)}. " if allowed else "")
    prompt = PROMPT.format(rubric=RUBRIC, name=name, statements=stmt_lines(stmts), scope=scope,
                           areas=", ".join(allowed or AREA_IDS))
    sids = {s["sid"] for s in stmts}
    extra = {"reasoning": {"effort": "low"}} if model == DS else {}
    for _ in range(3):
        d = llm.chat([{"role": "user", "content": prompt}], tag=tag, model=model,
                     max_tokens=24000 if model == DS else 12000, temperature=0, **extra)
        res = parse(d["choices"][0]["message"]["content"], sids, allowed)
        if res is not None:
            return res
    raise RuntimeError(f"{model}: no valid JSON for {name}")


def sign(v):
    return 0 if not v else (1 if v["stance"] > 0 else -1)


def label_member(pid, tag_prefix="", areas=None, old=None):
    """areas: relabel only these areas and keep the rest of `old` (the member's existing record)."""
    ev = json.loads((ROOT / "evidence" / f"{pid}.json").read_text())
    stmts, name = ev["statements"], ev["name"]
    rec = {"a": {}, "b": {}, "astra": None, "final": {}, "models": [NAMES[DS], NAMES[SOL]],
           "labeled": date.today().isoformat(), "n": len(stmts)}
    if not stmts:
        return rec
    todo = areas or AREA_IDS
    rec["a"] = ask(DS, name, stmts, f"{tag_prefix}regfocus_ds", allowed=areas)
    rec["b"] = ask(SOL, name, stmts, f"{tag_prefix}regfocus_sol", allowed=areas)
    disputed = [x for x in todo if sign(rec["a"].get(x)) != sign(rec["b"].get(x))]
    if disputed:
        cited = {s for x in disputed for j in ("a", "b") for s in (rec[j].get(x) or {}).get("sids", [])}
        sub = [s for s in stmts if s["sid"] in cited]
        try:
            rec["astra"] = ask(ASTRA, name, sub, f"{tag_prefix}regfocus_astra", allowed=disputed)
        except RuntimeError:   # no usable answer after retries: fall back to Sol, the stronger first judge
            rec["astra"], rec["astra_failed"] = {x: rec["b"][x] for x in disputed if x in rec["b"]}, True
    for x in todo:
        a, b = rec["a"].get(x), rec["b"].get(x)
        if x in disputed:
            v = rec["astra"].get(x)
            if v:
                rec["final"][x] = [v["stance"], v["sids"], v["why"]]
        elif a and b:
            st = min(abs(a["stance"]), abs(b["stance"])) * sign(a)
            rec["final"][x] = [st, list(dict.fromkeys(b["sids"] + a["sids"]))[:3], b["why"] or a["why"]]
    if areas and old:   # merge the relabeled areas into the existing record
        keep = lambda d: {k: v for k, v in (d or {}).items() if k not in areas}  # noqa: E731
        for j in ("a", "b", "final"):
            rec[j] = {**keep(old.get(j)), **rec[j]}
        if old.get("astra") is not None or rec["astra"] is not None:
            rec["astra"] = {**keep(old.get("astra")), **(rec["astra"] or {})}
    return rec


def load():
    return json.loads(OUT.read_text()) if OUT.exists() else {}


def save(data):
    OUT.write_text(json.dumps(data, indent=1, sort_keys=True))


def run(pids, workers=8, tag_prefix="", areas=None):
    """Label pids, saving as it goes. Stops cleanly at a budget cap."""
    data = load()
    done = 0

    def one(pid):
        try:
            return pid, label_member(pid, tag_prefix, areas, data.get(pid))
        except llm.BudgetExceeded:
            return pid, "budget"
        except Exception as e:  # noqa: BLE001  one member's failure must not stop the rest
            print(pid, "failed:", str(e)[:200], flush=True)
            return pid, None
    with ThreadPoolExecutor(workers) as ex:
        for fut in as_completed([ex.submit(one, p) for p in pids]):   # save in finish order, not submit order
            pid, rec = fut.result()
            if rec == "budget":
                print("budget cap reached; stopping", flush=True)
                break
            if rec is not None:
                data[pid] = rec
                done += 1
                if done % 20 == 0:
                    save(data)
                    print(done, "members", flush=True)
    save(data)
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--areas", help="relabel only these areas (comma-separated) for members already labeled")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    roster = [p["id"] for p in json.loads((ROOT / "data/roster.json").read_text())]
    pids = a.ids.split(",") if a.ids else roster
    have = load()
    areas = a.areas.split(",") if a.areas else None
    assert not areas or set(areas) <= set(AREA_IDS), "unknown area"
    if areas:
        pids = [p for p in pids if p in have]
    elif not a.redo:
        pids = [p for p in pids if p not in have]
    pids = pids[:a.limit] if a.limit else pids
    if a.dry_run:
        print(len(AREAS), "areas:", AREA_IDS)
        print(len(pids), "members to label")
        return
    print("labeled", run(pids, a.workers, areas=areas))


if __name__ == "__main__":
    main()
