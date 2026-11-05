"""Phase 3: score each person on 5 dimensions from verified statements only.

Two runs per person with differently shuffled statements; >=2 disagreement on any dimension
=> flagged for manual review, else averaged. Topics come from run A.

  python scripts/phase3_score.py sync --ids A,B      # regular calls (testing)
  python scripts/phase3_score.py submit               # OpenRouter batch (half price)
  python scripts/phase3_score.py collect              # poll + parse batch results
  python scripts/phase3_score.py combine              # write data/scores.json
"""
import json
import random
import re
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import llm  # noqa: E402

DIMS = ["ai_overall", "agi_pilled", "x_risk", "china_race", "regulation"]
TOPICS = ["jobs/economy", "China/competition", "national security", "kids/online safety", "deepfakes/elections",
          "copyright", "energy/data centers", "regulation", "AGI/transformative", "x-risk/loss of control",
          "misuse (bio/cyber)", "other"]
RUBRIC_TXT = (ROOT / "config/rubric.md").read_text()
RUBRIC_VERSION = re.search(r"rubric (v\d+)", RUBRIC_TXT).group(1)
PROMPT = (ROOT / "config/scoring_prompt.md").read_text().split("-->", 1)[1].strip()
RUBRIC = RUBRIC_TXT.split("-->", 1)[1].strip()
OUT = ROOT / "data/raw/scores"
OUT.mkdir(parents=True, exist_ok=True)
MAX_STMTS = 150
MAX_CHARS = 700
BATCH_URL = "https://openrouter.ai/api/v1/batches"


def select(stmts):
    """Cap very prolific people: keep all official/web, thin X posts evenly over time."""
    if len(stmts) <= MAX_STMTS:
        return stmts
    core = [s for s in stmts if s["origin"] != "x"]
    xs = sorted([s for s in stmts if s["origin"] == "x"], key=lambda s: s.get("date") or "")
    room = max(MAX_STMTS - len(core), 30)
    if len(core) > MAX_STMTS - 30:
        core = random.Random(0).sample(core, MAX_STMTS - 30)
    step = len(xs) / room if xs else 1
    xs = [xs[int(i * step)] for i in range(min(room, len(xs)))]
    return core + xs


def build(ev, seed):
    st = select(ev["statements"])
    st = st[:]
    random.Random(seed).shuffle(st)
    lines = []
    for s in st:
        t = re.sub(r"\s+", " ", s["text"])[:MAX_CHARS]
        lines.append(f"[{s['sid']}] ({s.get('date') or 'undated'}; {s['source_type']}) {t}")
    return PROMPT.format(rubric=RUBRIC, topics=", ".join(TOPICS), name=ev["name"], statements="\n".join(lines))


def parse(text):
    text = text or ""
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    for k in DIMS:
        v = d.get("dimensions", {}).get(k, {})
        sc = v.get("score")
        if isinstance(sc, str) and sc.strip().isdigit():
            v["score"] = int(sc)
        elif not isinstance(sc, int):
            v["score"] = "insufficient_evidence"
    return d


def people():
    roster = json.loads((ROOT / "data/roster.json").read_text())
    out = []
    for p in roster:
        ev = json.loads((ROOT / "evidence" / f"{p['id']}.json").read_text())
        if ev["statements"]:
            out.append(ev)
    return out


def sync(ids):
    for ev in [e for e in people() if e["id"] in ids]:
        for run, seed in (("A", 1), ("B", 2)):
            d = llm.chat([{"role": "user", "content": build(ev, seed)}], tag="phase3_sync", max_tokens=8000)
            res = parse(d["choices"][0]["message"]["content"])
            (OUT / f"{ev['id']}_{run}.json").write_text(json.dumps(res, indent=1))
            print(ev["name"], run, {k: res["dimensions"][k]["score"] for k in DIMS} if res else "PARSE FAIL",
                  f"${d['usage']['cost']:.3f}")


def submit(chunk=150):
    todo = [(ev, run, seed) for ev in people() for run, seed in (("A", 1), ("B", 2))
            if not (OUT / f"{ev['id']}_{run}.json").exists()]
    # budget pre-check: rough token estimate at batch prices ($1/$5 per M)
    est = sum(len(build(ev, seed)) / 3.5 for ev, _, seed in todo) / 1e6 * 1.0 + len(todo) * 2500 / 1e6 * 5.0
    left = llm.BUDGETS["openrouter"] - llm.spent("openrouter")
    print(f"{len(todo)} requests, est ${est:.2f}, budget left ${left:.2f}")
    if est > left:
        raise SystemExit("would exceed budget")
    headers = {"Authorization": f"Bearer {llm.os.environ['OPENROUTER_API_KEY']}"}
    ids_file = ROOT / "data/raw/score_batches.json"
    batches = json.loads(ids_file.read_text()) if ids_file.exists() else []
    for i in range(0, len(todo), chunk):
        part = todo[i:i + chunk]
        body = {"endpoint": "/v1/chat/completions", "model": llm.MODEL, "completion_window": "24h", "requests": [
            {"custom_id": f"{ev['id']}__{run}",
             "body": {"messages": [{"role": "user", "content": build(ev, seed)}], "max_tokens": 8000}}
            for ev, run, seed in part]}
        r = httpx.post(BATCH_URL, json=body, headers=headers, timeout=300)
        if r.status_code not in (200, 201, 202):
            raise SystemExit(f"batch submit failed {r.status_code}: {r.text[:500]}")
        bid = r.json()["id"]
        batches.append({"id": bid, "n": len(part), "logged": False})
        ids_file.write_text(json.dumps(batches, indent=1))
        print("submitted", bid, len(part))


def collect():
    headers = {"Authorization": f"Bearer {llm.os.environ['OPENROUTER_API_KEY']}"}
    ids_file = ROOT / "data/raw/score_batches.json"
    batches = json.loads(ids_file.read_text())
    while True:
        pending = 0
        for b in batches:
            if b.get("final"):
                continue
            d = httpx.get(f"{BATCH_URL}/{b['id']}", headers=headers, timeout=120).json()
            st = d.get("status")
            if st not in ("completed", "failed", "expired", "cancelled"):
                pending += 1
                continue
            b["final"] = st
            for res in d.get("results") or []:
                pid, run = res["custom_id"].rsplit("__", 1)
                if res.get("response") and res["response"].get("status_code") == 200:
                    body = res["response"]["body"]
                    parsed = parse(body["choices"][0]["message"]["content"])
                    if parsed:
                        (OUT / f"{pid}_{run}.json").write_text(json.dumps(parsed, indent=1))
            cost = float((d.get("usage") or {}).get("cost") or 0)
            if not b["logged"]:
                llm._log("openrouter", cost, "phase3_batch", {"batch_id": b["id"], "status": st})
                b["logged"] = True
            print(b["id"], st, d.get("request_counts"), f"${cost:.2f}")
        ids_file.write_text(json.dumps(batches, indent=1))
        if not pending:
            break
        time.sleep(60)


def combine():
    roster = json.loads((ROOT / "data/roster.json").read_text())
    out = {}
    for p in roster:
        a, b = OUT / f"{p['id']}_A.json", OUT / f"{p['id']}_B.json"
        if not a.exists():
            out[p["id"]] = {"dimensions": {k: {"score": "insufficient_evidence"} for k in DIMS},
                            "evidence_strength": "none", "summary": None, "flag": False,
                            "rubric_version": RUBRIC_VERSION}
            continue
        A = json.loads(a.read_text())
        B = json.loads(b.read_text()) if b.exists() else A
        dims, flag, why = {}, False, []
        for k in DIMS:
            sa, sb = A["dimensions"][k]["score"], B["dimensions"][k]["score"]
            if isinstance(sa, int) and isinstance(sb, int):
                if abs(sa - sb) >= 2:
                    flag, _ = True, why.append(f"{k}: {sa} vs {sb}")
                score = (sa + sb) / 2
            elif isinstance(sa, int) or isinstance(sb, int):
                # one run abstained: keep the number but mark as low-agreement
                score = sa if isinstance(sa, int) else sb
                why.append(f"{k}: one run insufficient")
            else:
                score = "insufficient_evidence"
            ids = list(dict.fromkeys((A["dimensions"][k].get("statement_ids") or []) + (B["dimensions"][k].get("statement_ids") or [])))
            dims[k] = {"score": score, "run_a": sa, "run_b": sb, "justification": A["dimensions"][k].get("justification"),
                       "statement_ids": ids[:6]}
        out[p["id"]] = {"dimensions": dims, "summary": A.get("summary"), "evidence_strength": A.get("evidence_strength"),
                        "topics": A.get("topics", {}), "flag": flag, "flag_reasons": why, "rubric_version": RUBRIC_VERSION}
    (ROOT / "data/scores.json").write_text(json.dumps(out, indent=1))
    print("scored", sum(1 for v in out.values() if v.get("summary")), "flagged", sum(v["flag"] for v in out.values()))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "sync":
        sync(set(sys.argv[3].split(",")) if len(sys.argv) > 3 else set())
    else:
        {"submit": submit, "collect": collect, "combine": combine}[cmd]()
