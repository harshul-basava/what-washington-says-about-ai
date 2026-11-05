"""Phase 1: find X handles for members-elect via Sonnet + Exa web search (2 searches max)."""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import llm  # noqa: E402

PROMPT = (ROOT / "config/handle_prompt.md").read_text().split("-->", 1)[1].strip()
OUT = ROOT / "data/raw/elect_handles.json"


def find(p):
    role = f"U.S. Senate from {p['state']}" if p["chamber"] == "senate" else f"U.S. House, {p['state']}-{p['district']}"
    tool = {"type": "openrouter:web_search", "parameters": {"engine": "exa", "max_results": 5, "max_uses": 2, "max_characters": 1500}}
    d = llm.chat([{"role": "user", "content": PROMPT.format(name=p["name"], role=role, party=p["party"])}],
                 tag="phase1_elect_handles", tools=[tool], max_tokens=1500)
    text = d["choices"][0]["message"].get("content") or ""
    m = re.findall(r"\{[\s\S]*\}", text)
    try:
        hs = json.loads(m[-1][m[-1].find("{"):])["handles"] if m else []
    except Exception:
        hs = []
    return p["id"], [{**h, "handle": h["handle"].lstrip("@").strip()} for h in hs if h.get("handle")]


if __name__ == "__main__":
    roster = json.loads((ROOT / "data/roster.json").read_text())
    done = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = [p for p in roster if p["status"] == "member_elect" and p["id"] not in done]
    with ThreadPoolExecutor(6) as ex:
        for pid, hs in ex.map(find, todo):
            done[pid] = hs
            OUT.write_text(json.dumps(done, indent=1))
    print("found handles for", sum(bool(v) for v in done.values()), "of", len(done))
    print("openrouter spent: $%.2f" % llm.spent("openrouter"))
