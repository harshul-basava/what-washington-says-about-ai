"""Quote verification: fetch the source URL and check the quote appears (fuzzy >= 0.9)."""
from __future__ import annotations

import html
import re
import unicodedata
from functools import lru_cache

import httpx
from rapidfuzz import fuzz

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
THRESHOLD = 90


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", html.unescape(s))
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("—", "-").replace("–", "-")
    s = re.sub(r"[^a-z0-9' ]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


@lru_cache(maxsize=4096)
def fetch_text(url: str) -> str | None:
    try:
        r = httpx.get(url, headers={"User-Agent": UA}, timeout=25, follow_redirects=True)
    except Exception:
        return None
    if r.status_code != 200:
        return None
    ct = r.headers.get("content-type", "")
    if "pdf" in ct or url.lower().endswith(".pdf"):
        try:
            import io
            from pypdf import PdfReader
            return norm(" ".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(r.content)).pages[:60]))
        except Exception:
            return None
    t = r.text
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return norm(t)


def segment_score(seg: str, page: str) -> float:
    seg = norm(seg)
    if len(seg) < 15:
        return 100.0
    if seg in page:
        return 100.0
    return fuzz.partial_ratio(seg, page)


def verify(quote: str, url: str, fallback_text: str | None = None) -> tuple[bool, float, str]:
    """Returns (verified, score, reason). Each '[...]'-separated segment must match.

    fallback_text: page text returned by the search engine (Exa) for this URL, used only
    when the live page can't be fetched (bot-blocked sites). Reason is then "ok_search_text".
    """
    page = fetch_text(url) if url else None
    via = "ok"
    if page is None and fallback_text:
        page, via = norm(fallback_text), "ok_search_text"
    if page is None:
        return False, 0.0, "fetch_failed"
    segs = [s for s in re.split(r"\[\s*(?:\.\.\.|…)\s*\]|\.\.\.|…", quote) if s.strip()]
    scores = [segment_score(s, page) for s in segs] or [0.0]
    sc = min(scores)
    return sc >= THRESHOLD, sc, via if sc >= THRESHOLD else "no_match"
