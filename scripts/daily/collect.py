"""Daily collection of new AI statements. Appends to evidence/{id}.json with new sids (never renumbers).

Sources:
  x     X full-archive search (paid API), many members' handles per query, since the last run.
  crec  Congressional Record (govinfo API), speaker identified by bioguide ID.
  chrg  Committee hearing transcripts (govinfo API), weekly; speakers matched by surname.
  web   Exa search (direct with EXA_API_KEY, else via OpenRouter) over a fixed pool of domains (official .gov sites + the news sites that produced
        quotes in the original collection), last 48 hours; DeepSeek extracts the member's own words,
        and every quote is checked against the page (verify.py).

Usage: python scripts/daily/collect.py [--sources x,crec,chrg,web] [--since YYYY-MM-DD] [--dry-run]
Each source is skipped (with a message) if its API key is missing. Needs: X_BEARER_TOKEN, GOVINFO_API_KEY (free, api.data.gov),
OPENROUTER_API_KEY (web search + extraction). EXA_API_KEY is optional (cheaper, date and domain filters).
"""
import argparse
import html
import json
import os
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from urllib.parse import unquote, urlparse

import httpx

from common import ROOT, append_statements, load_state, now_iso, roster, save_state, split_sentences, today
import llm
import verify
from phase2_assemble import AI_BARE, AI_STRONG, norm_date

X_KEYWORDS = '(AI OR "artificial intelligence" OR AGI OR superintelligence OR OpenAI OR Anthropic OR ChatGPT OR deepfake OR "machine learning" OR chatbot)'
X_QUERY_MAX = 1024
GOVINFO = "https://api.govinfo.gov"
EXTRACT_MODEL = "deepseek/deepseek-v4.1-flash"
MAX_EXCERPT = 900
MAX_WEB_PAGES = 80        # pages sent to the extraction model per run (newest-looking and official sites first)
WEB_MINUTES = 20          # time budget for page extraction
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
DATE_RX = re.compile(rf"\b(?:({MONTHS})\.?\s+(\d{{1,2}}),?\s+(20\d\d))\b|\b(20\d\d)-(\d\d)-(\d\d)\b")

# the web pool: domains that produced verified quotes in the original collection (see README "Sources")
POOL_OFFICIAL = ["house.gov", "senate.gov", "congress.gov"]
POOL_NEWS = ["foxnews.com", "thehill.com", "axios.com", "politico.com", "nextgov.com", "fedscoop.com", "rollcall.com",
             "washingtontimes.com", "pbs.org", "nbcnews.com", "cnbc.com", "newsweek.com", "meritalk.com",
             "washingtonreporter.news", "capitolreleases.com", "punchbowl.news", "semafor.com", "cnn.com",
             "washingtonpost.com", "nytimes.com", "apnews.com", "reuters.com", "statnews.com", "theverge.com"]
WEB_QUERIES = ["senator artificial intelligence", "congressman artificial intelligence", "congresswoman artificial intelligence",
               "AI legislation bill introduced", "AI safety Congress", "artificial general intelligence superintelligence Congress",
               "AI China competition Congress", "deepfake bill", "AI chatbot children Congress", "AI data centers energy Congress",
               "AI jobs workers Congress", "AI regulation federal preemption states"]
EXTRACT_PROMPT = """You are extracting public statements about artificial intelligence by specific U.S. politicians from one web page.

Page: {url}
Title: {title}
Published: {date}

Politicians to look for (extract only these people): {names}

Rules:
- Only include words that the named person said or wrote, copied **exactly** from the page text. No paraphrases.
- No words by other people (reporters, other politicians, experts), even when they are about this person.
- A statement is one to five sentences. Use "[...]" to join non-adjacent sentences from the same page.
- Only statements about AI (AI in general, AGI, AI risk, AI and China, AI rules, AI and jobs, deepfakes, chatbots, AI data centers, AI copyright, AI in defense). Skip trivial mentions.
- Watch for people with the same name. Returning nothing is a fine answer.

Page text:
<<<
{text}
>>>

Return only a JSON object:
{{"statements": [{{"name": "<name exactly as listed above>", "quote": "..."}}]}}"""


def log(*a):
    print(*a, flush=True)


def is_ai(text):
    body = re.sub(r"https?://\S+", "", text or "").strip()
    return len(body.split()) >= 8 and bool(AI_STRONG.search(body) or AI_BARE.search(body))


# ---------------------------------------------------------------- X
def x_people():
    return json.loads((ROOT / "data/x_people.json").read_text())


def x_queries(people):
    """Pack handles into OR-queries under X_QUERY_MAX characters."""
    tail = f") {X_KEYWORDS} -is:retweet"
    out, cur = [], []
    for h in sorted({h for p in people for h in p["handles"]}, key=str.lower):
        trial = "(" + " OR ".join(f"from:{x}" for x in cur + [h]) + tail
        if cur and len(trial) > X_QUERY_MAX:
            out.append("(" + " OR ".join(f"from:{x}" for x in cur) + tail)
            cur = []
        cur.append(h)
    if cur:
        out.append("(" + " OR ".join(f"from:{x}" for x in cur) + tail)
    return out


def collect_x(st, since=None, dry=False):
    from x_paid import search, slim_post
    people = x_people()
    owner = {h.lower(): p["id"] for p in people for h in p["handles"]}
    start = since or st["x"]["since"]
    end = (datetime.now(timezone.utc) - timedelta(minutes=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    qs = x_queries(people)
    log(f"x: {len(qs)} queries, {start} -> {end}")
    if dry:
        return {}
    found = defaultdict(list)
    for i, q in enumerate(qs, 1):
        posts, users, quoted, _, trunc = search(q, start, end_time=end, tag="daily_x", max_posts=2000)
        for t in posts:
            p = slim_post(t, users, quoted)
            pid = owner.get((p["author"] or "").lower())
            if not pid or not is_ai(p["text"]):
                continue
            found[pid].append({"text": p["text"].strip(), "date": norm_date(p["created_at"]), "url": p["url"], "source_type": "x",
                               "verified": True, "verified_via": "x_api", "origin": "x", "quoted": p.get("quoted")})
        log(f"  x query {i}/{len(qs)}: {len(posts)} posts{' (truncated)' if trunc else ''}")
    st["x"]["since"] = end
    return found


# ---------------------------------------------------------------- govinfo (Congressional Record, hearings)
def gov_get(path, **params):
    params["api_key"] = os.environ["GOVINFO_API_KEY"]
    for attempt in range(5):
        try:
            r = httpx.get(f"{GOVINFO}/{path}", params=params, timeout=60, follow_redirects=True)
        except httpx.TransportError:
            time.sleep(5 * 2**attempt)
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(10 * 2**attempt)
            continue
        r.raise_for_status()
        return r
    raise RuntimeError(f"govinfo failed: {path}")


def gov_packages(collection, since):
    out, mark = [], "*"
    while mark:
        d = gov_get(f"published/{since}", collection=collection, offsetMark=mark, pageSize=100).json()
        out += d.get("packages") or []
        nxt = d.get("nextPage")
        mark = unquote(re.search(r"offsetMark=([^&]+)", nxt).group(1)) if nxt else None
    return out


def page_text(htm):
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", htm)
    t = re.sub(r"(?s)<[^>]+>", "", t)
    return html.unescape(t)


SPEAKER = re.compile(r"^\s{1,}(?:Mr\.|Ms\.|Mrs\.|Miss|Dr\.|Senator|Chairman|Chairwoman|Chair|Representative|Ranking Member)\s+"
                     r"([A-Z][A-Z'\-]+(?:\s[A-Z][A-Z'\-]+)?)(?:\s+of\s+([A-Z][A-Za-z ]+?))?\.\s", re.M)


def speeches(text):
    """Split a transcript into (SURNAME, state or None, text) turns using the CR/hearing speaker markers."""
    marks = list(SPEAKER.finditer(text))
    for a, b in zip(marks, marks[1:] + [None]):
        yield a.group(1).strip(), (a.group(2) or "").strip() or None, text[a.end(): b.start() if b else len(text)]


def ai_excerpts(text):
    """AI-related excerpts (up to 5 sentences around each AI mention, <= MAX_EXCERPT chars), verbatim."""
    out = []
    for para in re.split(r"\n\s*\n|\n {2,}", text):
        para = " ".join(para.split())
        if not is_ai(para):
            continue
        sents = split_sentences(para)
        hits = [i for i, s in enumerate(sents) if AI_STRONG.search(s) or AI_BARE.search(s)]
        used = set()
        for i in hits:
            if i in used:
                continue
            win = list(range(max(0, i - 1), min(len(sents), i + 4)))
            used |= set(win)
            ex = " ".join(sents[j] for j in win)
            out.append(ex[:MAX_EXCERPT])
    return out


STATE_ABBR = {}


def _state_names():
    if not STATE_ABBR:
        STATE_ABBR.update({"Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
            "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
            "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
            "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
            "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
            "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
            "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
            "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"})
    return STATE_ABBR


def surname_index(members):
    """SURNAME -> [(bioguide, state)] from govinfo member records or roster entries."""
    idx = defaultdict(list)
    for m in members:
        last = m["last"].upper()
        idx[last].append((m["id"], m.get("state")))
        if " " in last:
            idx[last.split()[-1]].append((m["id"], m.get("state")))
    return idx


def resolve(idx, surname, state):
    cands = idx.get(surname.upper(), [])
    if state:
        ab = _state_names().get(state.strip())
        cands = [c for c in cands if c[1] in (ab, None)] if ab else cands
    ids = {c[0] for c in cands}
    return ids.pop() if len(ids) == 1 else None


def roster_members(chamber=None):
    legis = {m["id"]["bioguide"]: m for m in json.loads((ROOT / "data/ref/legislators-current.json").read_text())}
    out = []
    for p in roster():
        if p["status"] != "current" or (chamber and p["chamber"] != chamber):
            continue
        last = (legis.get(p["id"], {}).get("name", {}).get("last")) or p["name"].split()[-1]
        out.append({"id": p["id"], "last": last, "state": p["state"]})
    return out


def collect_crec(st, since=None, dry=False):
    start = since or st["crec"]["since"]
    known = {p["id"] for p in roster()}
    pkgs = gov_packages("CREC", start)
    log(f"crec: {len(pkgs)} issues since {start}")
    found = defaultdict(list)
    if dry:
        return found
    for pkg in pkgs:
        pid_pkg, mark = pkg["packageId"], "*"
        while mark:
            d = gov_get(f"packages/{pid_pkg}/granules", offsetMark=mark, pageSize=100).json()
            for g in d.get("granules") or []:
                if g.get("granuleClass") in ("DAILYDIGEST", "DIGEST") or re.search(r"PRAYER|PLEDGE|ADJOURN|RECESS", g.get("title") or ""):
                    continue
                gid = g["granuleId"]
                summ = gov_get(f"packages/{pid_pkg}/granules/{gid}/summary").json()
                mem = [{"id": m.get("bioGuideId"), "last": (m.get("memberName") or "").split(",")[0], "state": m.get("state")}
                       for m in summ.get("members") or [] if m.get("bioGuideId") in known]
                if not mem:
                    continue
                text = page_text(gov_get(f"packages/{pid_pkg}/granules/{gid}/htm").text)
                if not is_ai(" ".join(text.split())):
                    continue
                url = f"https://www.govinfo.gov/content/pkg/{pid_pkg}/html/{gid}.htm"
                day = summ.get("dateIssued") or pkg.get("dateIssued")
                turns = list(speeches(text))
                if g.get("granuleClass") == "EXTENSIONS" and len(mem) == 1:   # extension of remarks: one member's text
                    turns = [(mem[0]["last"].upper(), None, text)]
                idx = surname_index(mem)
                for sur, state, body in turns:
                    who = resolve(idx, sur, state)
                    if not who:
                        continue
                    for ex in ai_excerpts(body):
                        found[who].append({"text": ex, "date": norm_date(day), "url": url, "source_type": "floor", "verified": True,
                                           "verified_via": "govinfo_crec", "origin": "crec"})
            nxt = d.get("nextPage")
            mark = unquote(re.search(r"offsetMark=([^&]+)", nxt).group(1)) if nxt else None
    st["crec"]["since"] = today()
    return found


def collect_chrg(st, since=None, dry=False):
    """Hearings are published months late; run weekly (Mondays) or when --sources names it."""
    start = since or st["chrg"]["since"]
    pkgs = gov_packages("CHRG", start)
    log(f"chrg: {len(pkgs)} hearings published since {start}")
    found = defaultdict(list)
    if dry:
        return found
    house, senate = surname_index(roster_members("house")), surname_index(roster_members("senate"))
    for pkg in pkgs:
        pid_pkg = pkg["packageId"]
        summ = gov_get(f"packages/{pid_pkg}/summary").json()
        idx = senate if (summ.get("chamber") or "").upper() == "SENATE" or "shrg" in pid_pkg.lower() else house
        text = page_text(gov_get(f"packages/{pid_pkg}/htm").text)
        if not is_ai(" ".join(text.split())):
            continue
        url = f"https://www.govinfo.gov/content/pkg/{pid_pkg}/html/{pid_pkg}.htm"
        day = summ.get("heldDates", [summ.get("dateIssued")])[0] if summ.get("heldDates") else summ.get("dateIssued")
        for sur, state, body in speeches(text):
            who = resolve(idx, sur, state)
            if not who:
                continue
            for ex in ai_excerpts(body):
                found[who].append({"text": ex, "date": norm_date(day), "url": url, "source_type": "hearing", "verified": True,
                                   "verified_via": "govinfo_chrg", "origin": "chrg"})
    st["chrg"]["since"] = today()
    return found


# ---------------------------------------------------------------- web pool (Exa + DeepSeek extraction)
def name_patterns():
    """[(bioguide, display name, compiled regex)] for every roster person."""
    legis = {m["id"]["bioguide"]: m for m in json.loads((ROOT / "data/ref/legislators-current.json").read_text())}
    out = []
    for p in roster():
        nm = legis.get(p["id"], {}).get("name", {})
        forms = {p["name"]}
        if nm.get("official_full"):
            forms.add(nm["official_full"])
        if nm.get("first") and nm.get("last"):
            forms.add(f"{nm.get('nickname') or nm['first']} {nm['last']}")
            forms.add(f"{nm['first']} {nm['last']}")
        rx = re.compile(r"\b(?:" + "|".join(re.escape(f) for f in sorted(forms, key=len, reverse=True)) + r")\b")
        out.append((p["id"], p["name"], rx))
    return out


def site_owners():
    """Official website host -> bioguide (from congress-legislators)."""
    out = {}
    for m in json.loads((ROOT / "data/ref/legislators-current.json").read_text()):
        u = m["terms"][-1].get("url")
        if u:
            out[urlparse(u).netloc.lower().removeprefix("www.")] = m["id"]["bioguide"]
    return out


def page_date(page):
    """Best guess at a page's date: Exa's publishedDate, else the latest date written near the top of the page."""
    if page.get("publishedDate"):
        return page["publishedDate"][:10]
    best = None
    for m in DATE_RX.finditer((page.get("text") or "")[:4000]):
        try:
            if m.group(1):
                d = datetime.strptime(f"{m.group(1)[:3]} {m.group(2)} {m.group(3)}", "%b %d %Y").date().isoformat()
            else:
                d = date(int(m.group(4)), int(m.group(5)), int(m.group(6))).isoformat()
        except ValueError:
            continue
        best = max(best or d, d)
    return best


def is_recent(page, start):
    """Skip pages that are clearly older than the window (old year in the URL, or every date on the page is old)."""
    floor = (date.fromisoformat(start[:10]) - timedelta(days=3)).isoformat()
    y = re.search(r"/(20\d\d)/", page.get("url") or "")
    if y and y.group(1) < floor[:4]:
        return False
    d = page_date(page)
    return d is None or d >= floor


def extract(page, names):
    prompt = EXTRACT_PROMPT.format(url=page["url"], title=page.get("title") or "", date=page.get("publishedDate") or "unknown",
                                   names="; ".join(names), text=(page.get("text") or "")[:24000])
    d = llm.chat([{"role": "user", "content": prompt}], tag="daily_web_extract", model=EXTRACT_MODEL, max_tokens=12000, temperature=0,
                 reasoning={"effort": "low"})
    m = re.search(r"\{[\s\S]*\}", d["choices"][0]["message"]["content"] or "")
    if not m:
        return []
    try:
        return json.loads(m.group(0)).get("statements") or []
    except ValueError:
        return []


WEB_SEARCH_MODEL = "deepseek/deepseek-v4.1-flash"   # drives OpenRouter's Exa search when there is no EXA_API_KEY
WEB_SEARCH_PROMPT = """Search the web for pages published on or after {since} where a U.S. senator or representative \
makes a public statement about artificial intelligence. Topic: {query}.
Only use these sites: {domains}. Run several different searches. Do not answer the question; just list the pages you found
as a JSON list of URLs."""


def search_pages(q, doms, start):
    """[{url, title, publishedDate, text}] for one query over a domain pool.
    Uses Exa directly when EXA_API_KEY is set; otherwise OpenRouter's built-in Exa web search
    (same engine as the original collection), paid with the OpenRouter key."""
    if os.environ.get("EXA_API_KEY"):
        d = llm.exa_search({"query": q, "type": "auto", "numResults": 10, "includeDomains": doms, "startPublishedDate": start,
                            "contents": {"text": {"maxCharacters": 30000}}}, tag="daily_web_search")
        return d.get("results") or []
    tool = {"type": "openrouter:web_search", "parameters": {"engine": "exa", "max_results": 10, "max_uses": 3, "max_characters": 30000}}
    prompt = WEB_SEARCH_PROMPT.format(since=start[:10], query=q, domains=", ".join(doms))
    d = llm.chat([{"role": "user", "content": prompt}], tag="daily_web_search", tools=[tool], model=WEB_SEARCH_MODEL, max_tokens=2000)
    pages = {}
    for a in d["choices"][0]["message"].get("annotations") or []:
        c = a.get("url_citation") or {}
        if c.get("url") and c.get("content") and any(urlparse(c["url"]).netloc.lower().endswith(x) for x in doms):
            if len(c["content"]) > len(pages.get(c["url"], {}).get("text", "")):
                pages[c["url"]] = {"url": c["url"], "title": c.get("title"), "publishedDate": None, "text": c["content"]}
    return list(pages.values())


def collect_web(st, since=None, dry=False):
    start = since or (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen = set(st["web"]["seen"])
    owners, pats = site_owners(), name_patterns()
    name_of = {pid: nm for pid, nm, _ in pats}
    searches = [(q, POOL_OFFICIAL) for q in WEB_QUERIES] + [(q, POOL_NEWS) for q in WEB_QUERIES]
    log(f"web: {len(searches)} searches since {start}")
    found = defaultdict(list)
    if dry:
        return found
    pages = {}
    for q, doms in searches:
        for r in search_pages(q, doms, start):
            if r.get("url") and r["url"] not in seen:
                pages[r["url"]] = r
    log(f"  {len(pages)} new pages")
    cand = []
    for url, page in pages.items():
        seen.add(url)
        text = page.get("text") or ""
        if not is_recent(page, start) or not is_ai(" ".join(text.split())):
            continue
        host = urlparse(url).netloc.lower().removeprefix("www.")
        cands = [owners[host]] if host in owners and owners[host] in name_of else []
        cands += [pid for pid, _, rx in pats if pid not in cands and rx.search(text)]
        if cands:
            cand.append((0 if host.endswith(".gov") else 1, -(int((page_date(page) or "0").replace("-", "")) ), url, page, cands[:5]))
    cand.sort(key=lambda c: c[:2])
    log(f"  {len(cand)} recent AI pages that name a member; extracting up to {MAX_WEB_PAGES}")
    deadline = time.time() + WEB_MINUTES * 60

    def work(c):
        _, _, url, page, cands = c
        if time.time() > deadline:
            return []
        by_name = {name_of[x]: x for x in cands}
        out = []
        for s in extract(page, list(by_name)):
            pid, q = by_name.get(s.get("name")), (s.get("quote") or "").strip()
            if not pid or len(q.split()) < 8:
                continue
            ok, score, via = verify.verify(q, url, fallback_text=page.get("text"))
            if ok:
                out.append((pid, {"text": q, "date": page_date(page) or today(), "url": url,
                                  "source_type": "floor" if "congress.gov/congressional-record" in url else "web",
                                  "verified": True, "verified_via": via, "match_score": score, "origin": "web"}))
        return out
    with ThreadPoolExecutor(8) as ex:
        for res in ex.map(work, cand[:MAX_WEB_PAGES]):
            for pid, stmt in res:
                found[pid].append(stmt)
    st["web"]["seen"] = list(seen)
    st["web"]["since"] = now_iso()
    return found


# ---------------------------------------------------------------- main
NEEDS = {"x": ["X_BEARER_TOKEN"], "crec": ["GOVINFO_API_KEY"], "chrg": ["GOVINFO_API_KEY"], "web": ["OPENROUTER_API_KEY"]}
FUNCS = {"x": collect_x, "crec": collect_crec, "chrg": collect_chrg, "web": collect_web}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default="x,crec,web" + (",chrg" if date.today().weekday() == 0 else ""))
    ap.add_argument("--since", help="override the start date for every source (YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true", help="plan the queries but do not call paid APIs or write evidence")
    a = ap.parse_args(argv)
    st = load_state()
    report = {"sources": {}, "added": {}}
    for src in a.sources.split(","):
        missing = [k for k in NEEDS[src] if not os.environ.get(k)]
        if missing:
            log(f"{src}: skipped (missing {', '.join(missing)})")
            report["sources"][src] = f"skipped: missing {', '.join(missing)}"
            continue
        since = a.since and (f"{a.since}T00:00:00Z" if src in ("x", "web") else a.since)
        try:
            found = FUNCS[src](st, since, a.dry_run)
        except llm.BudgetExceeded as e:
            log(f"{src}: stopped, {e}")
            report["sources"][src] = f"budget: {e}"
            continue
        except Exception as e:  # noqa: BLE001  one source failing must not stop the others
            log(f"{src}: ERROR {str(e)[:300]}")
            report["sources"][src] = f"error: {str(e)[:300]}"
            continue
        n = 0
        if not a.dry_run:
            for pid, stmts in found.items():
                added = append_statements(pid, stmts)
                if added:
                    report["added"].setdefault(pid, []).extend(s["sid"] for s in added)
                    n += len(added)
        report["sources"][src] = f"ok: {n} new statements"
        log(f"{src}: {n} new statements")
        if not a.dry_run:
            save_state(st)
    if not a.dry_run:
        save_state(st)
    return report


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
