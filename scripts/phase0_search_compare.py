"""Phase 0: compare Exa vs native web search engines on 5 members."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROMPT = (ROOT / "config/research_prompt.md").read_text().split("-->", 1)[1].strip()
OUT = ROOT / "data/phase0_search_compare"
OUT.mkdir(parents=True, exist_ok=True)

PEOPLE = [
    ("Jay Obernolte", "U.S. Representative, R-CA"),
    ("Josh Hawley", "U.S. Senator, R-MO"),
    ("Maggie Hassan", "U.S. Senator, D-NH"),
    ("Glenn Grothman", "U.S. Representative, R-WI"),
    ("Sydney Kamlager-Dove", "U.S. Representative, D-CA"),
]


def parse(text: str) -> list:
    m = re.findall(r"\{[\s\S]*\"statements\"[\s\S]*\}", text)
    if not m:
        return []
    try:
        return json.loads(m[-1])["statements"]
    except Exception:
        s = m[-1]
        try:
            return json.loads(s[s.find("{"):])["statements"]
        except Exception:
            return []


def run(name, role, engine):
    tool = {"type": "openrouter:web_search",
            "parameters": {"engine": engine, "max_results": 10, "max_uses": 8}}
    if engine == "exa":
        tool["parameters"]["max_characters"] = 3000
    data = llm.chat([{"role": "user", "content": PROMPT.format(name=name, role=role)}],
                    tag=f"phase0_{engine}", tools=[tool], max_tokens=12000)
    text = data["choices"][0]["message"].get("content") or ""
    usage = data.get("usage", {})
    stmts = parse(text)
    return {"name": name, "engine": engine, "n": len(stmts), "cost": usage.get("cost"),
            "searches": (usage.get("server_tool_use_details") or {}).get("web_search_requests"),
            "usage": usage, "statements": stmts, "raw": text}


if __name__ == "__main__":
    for name, role in PEOPLE:
        for engine in ("exa", "native"):
            f = OUT / f"{name.replace(' ', '_')}_{engine}.json"
            if f.exists():
                continue
            res = run(name, role, engine)
            f.write_text(json.dumps(res, indent=1))
            print(f"{name:22} {engine:6} n={res['n']:3} searches={res['searches']} cost=${res['cost']}", flush=True)
    print("openrouter spent so far: $%.3f" % llm.spent("openrouter"))
