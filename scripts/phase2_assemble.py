"""Phase 2.4: merge CeSIA + X + web into evidence/{id}.json, deduplicated.

Statement: {sid, text, date, source_type (floor|hearing|x|web|official), url, verified, verified_via, origin}
"""
import json
import re
from datetime import datetime
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
EVD = ROOT / "evidence"
EVD.mkdir(exist_ok=True)

# X keyword search also hits "AI" as an unrelated acronym / name; require an AI-ish context word
# when the only match is the bare token "AI".
AI_STRONG = re.compile(r"artificial intelligence|\bAGI\b|superintelligen|OpenAI|Anthropic|ChatGPT|deepfake|machine learning|chatbot|\bA\.I\.|\bLLM", re.I)
AI_BARE = re.compile(r"\bAI\b")


def cesia_type(url):
    if "/CREC-" in url or "congressional-record" in url:
        return "floor"
    if "/meeting/" in url or "hearing" in url.lower() or "/event/" in url:
        return "hearing"
    return "official"


def norm_date(d):
    if not d:
        return None
    for fmt in ("%a %b %d %H:%M:%S %z %Y", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(d, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    m = re.match(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", str(d))
    return m.group(0) if m else None


def load_cesia():
    rows = json.loads((RAW / "cesia-data/q.json").read_text())["rows"]
    by = {}
    for r in rows:
        if r["j"] != "US":
            continue
        m = re.search(r"/([A-Z]\d{6})\.jpg", r.get("si") or "")
        if not m:
            continue
        # Only quote text, date, url, context: CeSIA's own labels (sc, st, t) are NOT passed on.
        by.setdefault(m.group(1), []).append({
            "text": r["q"], "date": r["d"], "url": r["u"], "source_type": cesia_type(r["u"]),
            "verified": True, "verified_via": "cesia_verbatim", "origin": "cesia", "context": r.get("c")})
    return by


def x_statements(pid):
    f = RAW / "x_emusks" / f"{pid}.json"
    if not f.exists():
        return []
    out = []
    for p in json.loads(f.read_text())["posts"]:
        t = (p.get("text") or "").strip()
        body = re.sub(r"https?://\S+", "", t).strip()
        if len(body.split()) < 8:
            continue
        if not AI_STRONG.search(body) and not AI_BARE.search(body):
            continue
        out.append({"text": t, "date": norm_date(p.get("created_at")), "url": p["url"], "source_type": "x",
                    "verified": True, "verified_via": "x_api", "origin": "x",
                    "quoted": p.get("quoted")})
    return out


def web_statements(pid):
    f = RAW / "web" / f"{pid}.json"
    if not f.exists():
        return []
    return [{**s, "date": norm_date(s.get("date")), "origin": "web"}
            for s in json.loads(f.read_text())["statements"] if s["verified"]]


def dedupe(stmts):
    keep = []
    for s in stmts:
        n = re.sub(r"\W+", " ", s["text"].lower()).strip()
        dup = False
        for k in keep:
            if fuzz.token_set_ratio(n, k["_n"]) >= 90 or (len(n) > 40 and (n in k["_n"] or k["_n"] in n)):
                dup = True
                k.setdefault("also_at", []).append(s["url"])
                break
        if not dup:
            keep.append({**s, "_n": n})
    for k in keep:
        k.pop("_n")
    return keep


def main():
    roster = json.loads((ROOT / "data/roster.json").read_text())
    cesia = load_cesia()
    stats = []
    for p in roster:
        # priority order on dedupe: official record > X (exact original) > web
        st = dedupe(cesia.get(p["id"], []) + x_statements(p["id"]) + web_statements(p["id"]))
        st.sort(key=lambda s: s.get("date") or "0000")
        for i, s in enumerate(st, 1):
            s["sid"] = f"s{i}"
        (EVD / f"{p['id']}.json").write_text(json.dumps({"id": p["id"], "name": p["name"], "statements": st}, indent=1))
        stats.append((p["id"], len(st), {o: sum(s["origin"] == o for s in st) for o in ("cesia", "x", "web")}))
    tot = {o: sum(x[2][o] for x in stats) for o in ("cesia", "x", "web")}
    print("people", len(stats), "statements", sum(x[1] for x in stats), tot)
    print("people with 0 statements:", sum(x[1] == 0 for x in stats))


if __name__ == "__main__":
    main()
