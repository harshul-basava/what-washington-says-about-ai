"""Single gateway for every paid API call (OpenRouter + X).

- Logs actual cost of each call to data/cost_ledger.jsonl.
- Hard-stops when ledger spend for a provider reaches budgets.yaml.
- Never prints or logs secrets.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
LEDGER = ROOT / "data" / "cost_ledger.jsonl"
BUDGETS = yaml.safe_load((ROOT / "budgets.yaml").read_text())

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "anthropic/claude-sonnet-5.5"  # switch provider/model here only
X_PRICE_PER_POST = 0.005
X_PRICE_PER_COUNTS_REQ = 0.01


class BudgetExceeded(RuntimeError):
    pass


def spent(provider: str) -> float:
    if not LEDGER.exists():
        return 0.0
    total = 0.0
    for line in LEDGER.read_text().splitlines():
        rec = json.loads(line)
        if rec["provider"] == provider:
            total += rec["cost"]
    return total


def spent_this_month(provider: str) -> float:
    """Spend for a provider since the first day of the current UTC month."""
    if not LEDGER.exists():
        return 0.0
    t = time.gmtime()
    start = time.mktime((t.tm_year, t.tm_mon, 1, 0, 0, 0, 0, 0, 0)) - time.timezone
    total = 0.0
    for line in LEDGER.read_text().splitlines():
        rec = json.loads(line)
        if rec["provider"] == provider and rec["ts"] >= start:
            total += rec["cost"]
    return total


def _check(provider: str) -> None:
    s = spent(provider)
    if s >= BUDGETS.get(provider, float("inf")):
        raise BudgetExceeded(f"{provider} spend ${s:.2f} >= budget ${BUDGETS[provider]}")
    cap = (BUDGETS.get("monthly") or {}).get(provider)
    if cap is not None and (m := spent_this_month(provider)) >= cap:
        raise BudgetExceeded(f"{provider} spend this month ${m:.2f} >= monthly budget ${cap}")


def _log(provider: str, cost: float, tag: str, meta: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as f:
        f.write(json.dumps({"ts": time.time(), "provider": provider, "cost": cost, "tag": tag, **meta}) + "\n")


def chat(messages: list[dict], *, tag: str, tools: list | None = None, model: str = MODEL,
         response_format: dict | None = None, max_tokens: int = 8000, **extra) -> dict:
    """One OpenRouter chat completion. Returns the raw response JSON."""
    _check("openrouter")
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, **extra}
    if tools:
        body["tools"] = tools
    if response_format:
        body["response_format"] = response_format
    headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
    for attempt in range(4):
        try:
            r = httpx.post(OPENROUTER_URL, json=body, headers=headers, timeout=600)
        except (httpx.TimeoutException, httpx.TransportError):
            if attempt < 3:
                time.sleep(5 * 2**attempt)
                continue
            raise
        if r.status_code in (429, 500, 502, 503) and attempt < 3:
            time.sleep(5 * 2**attempt)
            continue
        break
    if r.status_code != 200:
        raise RuntimeError(f"OpenRouter {r.status_code}: {r.text[:500]}")
    data = r.json()
    usage = data.get("usage") or {}
    cost = float(usage.get("cost") or 0.0)
    _log("openrouter", cost, tag, {"model": model, "usage": usage, "gen_id": data.get("id")})
    return data


def x_get(path: str, params: dict, *, tag: str) -> dict:
    """GET an X API v2 endpoint; cost estimated from the published per-unit prices."""
    _check("x")
    headers = {"Authorization": f"Bearer {os.environ['X_BEARER_TOKEN']}"}
    for attempt in range(5):
        r = httpx.get(f"https://api.x.com/2/{path}", params=params, headers=headers, timeout=60)
        if r.status_code == 429 and attempt < 4:
            reset = int(r.headers.get("x-rate-limit-reset", time.time() + 60))
            time.sleep(max(1, reset - time.time()) + 1)
            continue
        break
    if r.status_code != 200:
        raise RuntimeError(f"X {r.status_code}: {r.text[:500]}")
    data = r.json()
    if path.startswith("tweets/counts"):
        cost = X_PRICE_PER_COUNTS_REQ
    else:
        cost = X_PRICE_PER_POST * len(data.get("data") or [])
    _log("x", cost, tag, {"path": path, "n": len(data.get("data") or [])})
    time.sleep(1.05)  # full-archive: 1 req/sec
    return data


EXA_URL = "https://api.exa.ai/search"
EXA_EST_PER_SEARCH = 0.007  # used only if Exa's response has no costDollars


def exa_search(body: dict, *, tag: str) -> dict:
    """One Exa search (with page text). Logs Exa's reported cost; capped like the other providers."""
    _check("exa")
    headers = {"x-api-key": os.environ["EXA_API_KEY"], "Content-Type": "application/json"}
    for attempt in range(4):
        try:
            r = httpx.post(EXA_URL, json=body, headers=headers, timeout=120)
        except (httpx.TimeoutException, httpx.TransportError):
            if attempt < 3:
                time.sleep(5 * 2**attempt)
                continue
            raise
        if r.status_code in (429, 500, 502, 503) and attempt < 3:
            time.sleep(5 * 2**attempt)
            continue
        break
    if r.status_code != 200:
        raise RuntimeError(f"Exa {r.status_code}: {r.text[:500]}")
    data = r.json()
    cost = float((data.get("costDollars") or {}).get("total") or EXA_EST_PER_SEARCH)
    _log("exa", cost, tag, {"n": len(data.get("results") or [])})
    return data
