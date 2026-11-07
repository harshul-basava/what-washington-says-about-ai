"""Phase 2 (X, paid): AI-related posts via the X API v2 full-archive search.

Same output schema as x_emusks.mjs (data/raw/x_emusks/{id}.json) so the finalize/assemble steps
don't care which collector produced a file. Skips people that already have a file.
Usage: uv run python scripts/x_paid.py data/x_people_prelim.json [more.json ...] [--limit N]
Cost: $0.005 per returned post, capped at MAX_POSTS per person (newest first; `truncated` flags it).
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import llm  # noqa: E402

OUT = ROOT / "data/raw/x_emusks"
KEYWORDS = '(AI OR "artificial intelligence" OR AGI OR superintelligence OR OpenAI OR Anthropic OR ChatGPT OR deepfake OR "machine learning" OR chatbot)'
START = "2023-01-01T00:00:00Z"
MAX_POSTS = 500


def search(query, start_time, *, tag, max_posts=MAX_POSTS, end_time=None):
    """Full-archive search, newest first. Returns (posts, users, quoted, pages, truncated)."""
    params = {"query": query, "start_time": start_time, "max_results": 100,
              "tweet.fields": "created_at,lang,referenced_tweets,author_id,note_tweet",
              "expansions": "author_id,referenced_tweets.id",
              "user.fields": "name,username,public_metrics"}
    if end_time:
        params["end_time"] = end_time
    posts, users, quoted, pages, token = [], {}, {}, 0, None
    while len(posts) < max_posts:
        if token:
            params["next_token"] = token
        params["max_results"] = max(10, min(100, max_posts - len(posts)))
        d = llm.x_get("tweets/search/all", params, tag=tag)
        pages += 1
        inc = d.get("includes") or {}
        for u in inc.get("users", []):
            users[u["id"]] = u
        for t in inc.get("tweets", []):
            quoted[t["id"]] = (t.get("note_tweet") or {}).get("text") or t.get("text")
        posts += d.get("data") or []
        token = (d.get("meta") or {}).get("next_token")
        if not token:
            break
    return posts, users, quoted, pages, bool(token)


def slim_post(t, users, quoted):
    """One post in the collector's output schema."""
    u = users.get(t.get("author_id"), {})
    refs = {r["type"]: r["id"] for r in t.get("referenced_tweets", [])}
    text = (t.get("note_tweet") or {}).get("text") or t["text"]
    author = u.get("username", "")
    return {"id": t["id"], "text": text, "created_at": t.get("created_at"), "author": author,
            "lang": t.get("lang"), "is_reply": "replied_to" in refs,
            "quoted": quoted.get(refs.get("quoted")), "url": f"https://x.com/{author}/status/{t['id']}"}


def collect(person):
    handles = person["handles"]
    query = "(" + " OR ".join(f"from:{h}" for h in handles) + f") {KEYWORDS} -is:retweet"
    posts, users, quoted, pages, truncated = search(query, START, tag=f"x_paid:{person['id']}")
    token = truncated
    raw, slim = [], []
    for t in posts:
        u = users.get(t.get("author_id"), {})
        refs = {r["type"]: r["id"] for r in t.get("referenced_tweets", [])}
        text = (t.get("note_tweet") or {}).get("text") or t["text"]
        author = u.get("username", "")
        user = {"id": u.get("id"), "name": u.get("name"), "username": author,
                "stats": {"posts": (u.get("public_metrics") or {}).get("tweet_count")}}
        raw.append({**t, "user": user})
        slim.append({"id": t["id"], "text": text, "created_at": t.get("created_at"), "author": author,
                     "lang": t.get("lang"), "is_reply": "replied_to" in refs,
                     "quoted": quoted.get(refs.get("quoted")), "url": f"https://x.com/{author}/status/{t['id']}"})
    return {"id": person["id"], "handles": handles, "query": query, "pages": pages, "n": len(slim),
            "source": "x_api_full_archive", "truncated": bool(token),
            "collected_at": datetime.now(timezone.utc).isoformat(), "posts": slim, "raw": raw}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    people, seen = [], set()
    for f in a.files:
        for p in json.loads(Path(f).read_text()):
            if p["id"] not in seen and p.get("handles") and not (OUT / f"{p['id']}.json").exists():
                seen.add(p["id"])
                people.append(p)
    people = people[: a.limit] if a.limit else people
    print(f"{len(people)} people to collect; X spent so far ${llm.spent('x'):.2f}", flush=True)
    for i, p in enumerate(people, 1):
        try:
            r = collect(p)
        except llm.BudgetExceeded:
            print("X budget reached; stopping", flush=True)
            break
        except Exception as e:  # noqa: BLE001
            print(f"[{i}] {p['id']} ERROR {str(e)[:200]}", flush=True)
            continue
        (OUT / f"{p['id']}.json").write_text(json.dumps(r))
        print(f"[{i}/{len(people)}] {p['id']} {r['n']} posts{' (truncated)' if r['truncated'] else ''} "
              f"· X ${llm.spent('x'):.2f}", flush=True)


if __name__ == "__main__":
    main()
