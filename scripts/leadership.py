"""Who backs Chuck Schumer (Senate) and Hakeem Jeffries (House) as Democratic leader in the next Congress.

Local research only: not on the site. Covers every Democrat in the roster (current and members-elect, plus the
independents who caucus with Democrats). For each member:
  1. DeepSeek V4.1 Flash runs OpenRouter's Exa web search and returns evidence: exact sentences from pages
     (the member's own words, or a reporter's sentence about their position) with the URL.
  2. Each sentence is checked against the page (verify.py, fuzzy match >= 90). Unverified evidence is dropped.
  3. GPT-6.1 Sol reads only the verified evidence and decides the stance:
     support / oppose / uncommitted / none (no public position found).

Writes data/leadership.json (git-ignored) and local/leadership.html (git-ignored), then you open the page.
Usage: python scripts/leadership.py [--ids A,B] [--limit N] [--redo] [--workers 8] [--page-only]
"""
import argparse
import html
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import llm  # noqa: E402
import verify  # noqa: E402

OUT = ROOT / "data/leadership.json"
PAGE = ROOT / "local/leadership.html"
DS, SOL = "deepseek/deepseek-v4.1-flash", "openai/gpt-6.1-sol"
DEMS = {"Democrat", "Democratic", "DFL"}
CAUCUS_INDEPENDENTS = {"S000033", "K000383"}   # Sanders, King
LEADER = {"senate": ("Chuck Schumer", "Senate Democratic leader (majority leader)"),
          "house": ("Hakeem Jeffries", "House Democratic leader and Speaker")}

SEARCH_PROMPT = """Today is {today}. Democrats won control of Congress on November 3, 2026, and will soon choose their leaders.
Find out whether {name} ({role}) has said publicly whether they will support {leader} as {post} in the new Congress.
Campaign pledges count (for example "I will not vote for {leader} as leader"). Also count a clear statement of support,
a call for "new leadership", or a refusal to commit.

Search the web (news reports, the member's own site and posts). Look for the newest statements first.

Return only JSON:
```json
{{"evidence": [{{"text": "exact sentence copied word for word from the page", "url": "https://...", "date": "YYYY-MM-DD or null",
  "kind": "quote or report"}}]}}
```
"quote" = the member's own words. "report" = a reporter's sentence that states the member's position.
Copy text exactly; do not paraphrase. Give at most 4 items, only about {name} and {leader}'s leadership.
If you find nothing, return {{"evidence": []}}."""

JUDGE_PROMPT = """Decide {name}'s public position on {leader} as {post} in the new Congress (after the Nov 3, 2026 election),
using only this verified evidence:

{evidence}

Stances:
- "support": says they will vote for or back {leader} as leader.
- "oppose": says they will not vote for {leader}, or wants someone else / "new leadership".
- "uncommitted": publicly declined to commit, or said they are undecided.
- "none": the evidence does not show their own position.
If statements conflict, use the newest one.

Return only JSON: {{"stance": "...", "best": [indexes of the 1-2 items that show it best], "why": "one plain sentence"}}"""


def load():
    return json.loads(OUT.read_text()) if OUT.exists() else {}


def save(d):
    OUT.write_text(json.dumps(d, indent=1, sort_keys=True))


def members():
    roster = json.loads((ROOT / "data/roster.json").read_text())
    nxt = json.loads((ROOT / "data/next_congress.json").read_text())
    out = []
    for p in roster:
        if p["party"] in DEMS or p["id"] in CAUCUS_INDEPENDENTS:
            out.append({**p, "next": (nxt.get(p["id"]) or {}).get("status")})
    return out


def role(p):
    pa = "I" if p["id"] in CAUCUS_INDEPENDENTS else "D"
    if p["chamber"] == "senate":
        r = f"U.S. Senator, {pa}-{p['state']}"
    else:
        r = f"U.S. Representative, {pa}-{p['state']}-{p['district'] if p['district'] not in (0, None) else 'AL'}"
    return r + (" (elected Nov 2026, takes office Jan 2027)" if p["status"] == "member_elect" else "")


def jparse(text):
    m = re.search(r"\{[\s\S]*\}", text or "")
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except ValueError:
        return None


def research(p):
    leader, post = LEADER[p["chamber"]]
    if p["id"] in ("J000294", "S000148"):   # the leaders themselves
        return {"stance": "self", "why": "This is the leader.", "evidence": [], "leader": leader}
    tool = {"type": "openrouter:web_search", "parameters": {"engine": "exa", "max_results": 6, "max_uses": 2, "max_characters": 6000}}
    prompt = SEARCH_PROMPT.format(today=date.today().isoformat(), name=p["name"], role=role(p), leader=leader, post=post)
    d = llm.chat([{"role": "user", "content": prompt}], tag="leadership_search", tools=[tool], model=DS,
                 max_tokens=16000, temperature=0, reasoning={"effort": "low"})
    msg = d["choices"][0]["message"]
    pages = {}
    for a in msg.get("annotations") or []:
        c = a.get("url_citation") or {}
        if c.get("url") and c.get("content"):
            pages[c["url"]] = max(pages.get(c["url"], ""), c["content"], key=len)
    ev = []
    for e in ((jparse(msg.get("content")) or {}).get("evidence") or [])[:4]:
        t, u = str(e.get("text") or "").strip(), str(e.get("url") or "").strip()
        if len(t) < 20 or not u.startswith("http"):
            continue
        ok, score, via = verify.verify(t, u, fallback_text=pages.get(u))
        ev.append({"text": t[:800], "url": u, "date": e.get("date"), "kind": e.get("kind"), "verified": ok, "via": via})
    good = [e for e in ev if e["verified"]]
    rec = {"leader": leader, "evidence": ev, "searched": date.today().isoformat(), "stance": "none", "why": "", "best": []}
    if good:
        lines = "\n".join(f"[{i}] ({e['date'] or 'undated'}; {e['kind']}; {e['url']}) {e['text']}" for i, e in enumerate(good))
        for _ in range(2):
            j = jparse(llm.chat([{"role": "user", "content": JUDGE_PROMPT.format(name=p["name"], leader=leader, post=post, evidence=lines)}],
                                tag="leadership_judge", model=SOL, max_tokens=4000, temperature=0)["choices"][0]["message"]["content"])
            if j and j.get("stance") in ("support", "oppose", "uncommitted", "none"):
                rec.update(stance=j["stance"], why=str(j.get("why") or "")[:300],
                           best=[good[i] for i in (j.get("best") or []) if isinstance(i, int) and 0 <= i < len(good)][:2])
                break
    return rec


def run(ps, workers):
    data = load()
    n = 0

    def one(p):
        try:
            return p["id"], research(p)
        except llm.BudgetExceeded:
            return p["id"], "budget"
        except Exception as e:  # noqa: BLE001
            print(p["id"], "failed:", str(e)[:200], flush=True)
            return p["id"], None
    with ThreadPoolExecutor(workers) as ex:
        for fut in as_completed([ex.submit(one, p) for p in ps]):
            pid, rec = fut.result()
            if rec == "budget":
                print("budget cap reached; stopping", flush=True)
                break
            if rec:
                data[pid] = rec
                n += 1
                if n % 20 == 0:
                    save(data)
                    print(n, "members", flush=True)
    save(data)
    return n


# ---------- local page ----------
ORDER = ["oppose", "uncommitted", "support", "none"]
LABEL = {"oppose": "Opposes", "uncommitted": "Won't commit", "support": "Supports", "none": "No public position found"}


def page():
    data, ms = load(), {p["id"]: p for p in members()}
    esc = html.escape
    parts = []
    for ch in ("senate", "house"):
        leader = LEADER[ch][0]
        rows = [(ms[i], r) for i, r in data.items() if i in ms and ms[i]["chamber"] == ch and r["stance"] != "self"]
        counts = {s: sum(r["stance"] == s for _, r in rows) for s in ORDER}
        nextc = [(m, r) for m, r in rows if m["next"] != "departing"]
        cn = {s: sum(r["stance"] == s for _, r in nextc) for s in ORDER}
        parts.append(f"<section><h2>{'Senate' if ch == 'senate' else 'House'}: {esc(leader)}</h2>"
                     f"<p class=sum>{len(rows)} Democrats checked. In the incoming caucus ({len(nextc)}): "
                     + " · ".join(f"<b class='s-{s}'>{cn[s]}</b> {LABEL[s].lower()}" for s in ORDER)
                     + f". All checked, including departing members: " + ", ".join(f"{counts[s]} {LABEL[s].lower()}" for s in ORDER) + ".</p>")
        for s in ORDER:
            grp = sorted([(m, r) for m, r in rows if r["stance"] == s], key=lambda x: (x[0]["status"] != "member_elect", x[0]["name"]))
            if not grp:
                continue
            parts.append(f"<details {'open' if s != 'none' else ''}><summary><span class='dot s-{s}'></span>{LABEL[s]} ({len(grp)})</summary><table>")
            for m, r in grp:
                tag = {"member_elect": "elect", "current": ""}[m["status"]] or ("leaving" if m["next"] == "departing" else "")
                seat = m["state"] + ("" if ch == "senate" else f"-{m['district'] if m['district'] not in (0, None) else 'AL'}")
                ev = r.get("best") or ([e for e in r["evidence"] if e["verified"]][:1] if s != "none" else [])
                evh = "".join(f"<blockquote>“{esc(e['text'])}” <a href='{esc(e['url'])}' target=_blank rel=noopener>"
                              f"{esc(re.sub(r'^www\\.', '', e['url'].split('/')[2]))}</a>{' · ' + esc(str(e['date'])) if e.get('date') else ''}"
                              f"{' · reported' if e.get('kind') == 'report' else ''}</blockquote>" for e in ev)
                parts.append(f"<tr><td class=nm>{esc(m['name'])}<span class=seat>{seat}</span>{f'<span class=tag>{tag}</span>' if tag else ''}</td>"
                             f"<td>{esc(r.get('why') or '')}{evh}</td></tr>")
            parts.append("</table></details>")
        parts.append("</section>")
    stamp = max((r.get("searched", "") for r in data.values()), default="")
    PAGE.parent.mkdir(exist_ok=True)
    PAGE.write_text(f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Democratic Leadership Votes</title><style>
:root{{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--line:#e4e1da;--card:#fff;--op:#c2412d;--un:#b7791f;--su:#2f6db5;--no:#9a9893}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151514;--fg:#ecebe7;--mut:#a3a19b;--line:#2f2e2b;--card:#1d1d1b;--op:#e8735f;--un:#e0a84a;--su:#6aa2e6;--no:#77756f}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,sans-serif;margin:0;padding:24px 16px 64px}}
main{{max-width:980px;margin:auto}}h1{{font-size:26px;margin:0 0 4px}}.lede{{color:var(--mut);margin:0 0 24px}}
h2{{font-size:20px;margin:32px 0 6px}}.sum{{margin:0 0 12px}}
details{{background:var(--card);border:1px solid var(--line);border-radius:8px;margin:8px 0;padding:6px 12px}}
summary{{cursor:pointer;font-weight:600;padding:4px 0}}.dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:8px}}
.s-oppose{{color:var(--op)}}.dot.s-oppose{{background:var(--op)}}.s-uncommitted{{color:var(--un)}}.dot.s-uncommitted{{background:var(--un)}}
.s-support{{color:var(--su)}}.dot.s-support{{background:var(--su)}}.s-none{{color:var(--no)}}.dot.s-none{{background:var(--no)}}
table{{width:100%;border-collapse:collapse}}td{{border-top:1px solid var(--line);padding:8px 6px;vertical-align:top}}
.nm{{width:220px;font-weight:600}}.seat{{display:block;font-weight:400;color:var(--mut);font-size:13px}}
.tag{{font-size:11px;font-weight:500;border:1px solid var(--line);border-radius:4px;padding:0 4px;color:var(--mut)}}
blockquote{{margin:6px 0 0;padding-left:10px;border-left:2px solid var(--line);color:var(--mut);font-size:14px}}a{{color:inherit}}
@media (max-width:600px){{.nm{{width:110px}}}}
</style></head><body><main><h1>Who backs Schumer and Jeffries as leader</h1>
<p class=lede>Democratic senators and representatives, current and newly elected. Each position comes from a web search and is checked against
the source page; a model reads only the checked text and decides the position. "No public position found" means the search found nothing,
not that the member has no view. Searched {esc(stamp)}. Local page; not on the site.</p>{''.join(parts)}</main></body></html>""")
    return PAGE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--page-only", action="store_true")
    a = ap.parse_args()
    if not a.page_only:
        ms, have = members(), load()
        ps = [m for m in ms if (not a.ids or m["id"] in a.ids.split(",")) and (a.redo or a.ids or m["id"] not in have)]
        ps = ps[:a.limit] if a.limit else ps
        print(len(ps), "members to search", flush=True)
        print("searched", run(ps, a.workers))
    print(page())


if __name__ == "__main__":
    main()
