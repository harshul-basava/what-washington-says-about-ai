"""Phase 2.3: web research per person (Sonnet 5.5 + Exa), then verify each quote.

Writes data/raw/web/{id}.json with raw model output, Exa page texts (annotations), and
verified statements. Usage: python scripts/phase2_web.py [--ids id1,id2] [--limit N] [--workers 6]
"""
import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import llm  # noqa: E402
import verify  # noqa: E402

PROMPT_FILE = ROOT / "config/research_prompt.md"
PROMPT_VERSION = re.search(r"research_prompt (v\d+)", PROMPT_FILE.read_text()).group(1)
PROMPT = PROMPT_FILE.read_text().split("-->", 1)[1].strip()
OUT = ROOT / "data/raw/web"
OUT.mkdir(parents=True, exist_ok=True)

PARTY = {"Democrat": "D", "Democratic": "D", "Republican": "R", "Independent": "I", "DFL": "D"}


def role(p):
    pa = PARTY.get(p["party"], p["party"][:1] if p["party"] else "?")
    if p["chamber"] == "senate":
        r = f"U.S. Senator, {pa}-{p['state']}"
    else:
        d = "at-large" if p["district"] in (0, "0", None) else p["district"]
        r = f"U.S. Representative, {pa}-{p['state']}-{d}"
    if p["status"] == "member_elect":
        r += " (elected Nov 2026, not yet sworn in; previous roles count too)"
    return r


def parse(text):
    m = re.findall(r"\{[\s\S]*\"statements\"[\s\S]*\}", text or "")
    if not m:
        return []
    s = m[-1]
    for cand in (s, s[s.find("{"):]):
        try:
            return json.loads(cand)["statements"]
        except Exception:
            pass
    return []


def research(p):
    f = OUT / f"{p['id']}.json"
    if f.exists():
        return json.loads(f.read_text())
    tool = {"type": "openrouter:web_search",
            "parameters": {"engine": "exa", "max_results": 10, "max_uses": 8, "max_characters": 6000}}
    d = llm.chat([{"role": "user", "content": PROMPT.format(name=p["name"], role=role(p))}],
                 tag="phase2_web", tools=[tool], max_tokens=12000)
    msg = d["choices"][0]["message"]
    pages = {}
    for a in msg.get("annotations") or []:
        c = a.get("url_citation") or {}
        if c.get("url") and c.get("content"):
            pages[c["url"]] = max(pages.get(c["url"], ""), c["content"], key=len)
    stmts = []
    for i, s in enumerate(parse(msg.get("content"))):
        q, u = (s.get("quote") or "").strip(), (s.get("url") or "").strip()
        if not q or not u:
            continue
        ok, score, why = verify.verify(q, u, fallback_text=pages.get(u))
        stmts.append({"text": q, "url": u, "date": s.get("date"), "venue": s.get("venue"), "source_type": "web",
                      "verified": ok, "verified_via": why, "match_score": round(score, 1)})
    out = {"id": p["id"], "name": p["name"], "prompt_version": PROMPT_VERSION, "cost": d["usage"].get("cost"),
           "searches": (d["usage"].get("server_tool_use_details") or {}).get("web_search_requests"),
           "statements": stmts, "raw": msg.get("content"), "pages": pages}
    f.write_text(json.dumps(out, indent=1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    roster = json.loads((ROOT / "data/roster.json").read_text())
    if a.ids:
        want = set(a.ids.split(","))
        roster = [p for p in roster if p["id"] in want]
    if a.limit:
        roster = roster[: a.limit]

    def safe(p):
        try:
            return research(p)
        except llm.BudgetExceeded:
            raise
        except Exception as e:  # keep going; failed people simply get retried next run
            print(f"FAIL {p['id']}: {str(e)[:200]}", flush=True)
            return None

    n = 0
    with ThreadPoolExecutor(a.workers) as ex:
        for r in ex.map(safe, roster):
            if r:
                n += 1
                v = sum(s["verified"] for s in r["statements"])
                if n % 20 == 0 or a.ids:
                    print(f"{n}/{len(roster)} {r['name'][:24]:24} found={len(r['statements'])} verified={v} cost=${r['cost']:.3f}", flush=True)
    print("openrouter spent: $%.2f" % llm.spent("openrouter"))


if __name__ == "__main__":
    main()
