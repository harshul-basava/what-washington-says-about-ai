# Phase 0 findings (verified 2026-11-05)

Spend in Phase 0: **OpenRouter $2.98, X $0.02.**

## OpenRouter

Source: OpenRouter `/api/v1/models` (live), plus these docs: [web search](https://openrouter.ai/docs/guides/features/server-tools/web-search), [server tools](https://openrouter.ai/docs/guides/features/server-tools), [batch](https://openrouter.ai/docs/batch-quickstart), and [usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting).

| Item | Finding |
|---|---|
| Model slug | `anthropic/claude-sonnet-5.5`. Confirmed. |
| Price | $2 in / $10 out per 1M tokens. The 1M context is confirmed. |
| Batch variant | `anthropic/claude-sonnet-5.5:batch` at $1 / $5. **Use it for scoring.** |
| Key | Limit is $200. $200 remaining at the start. |
| Web search syntax | `{"type":"openrouter:web_search","parameters":{"engine":"exa","max_results":10,"max_uses":8,"max_characters":N}}` |
| Exa price | $0.007 per search, covering up to 10 results. Additional results cost $0.001 each. |
| Search cap | `max_uses` caps the searches in one request (we use 8). |
| Web search in batch | **No.** Batch rejects `engine` other than auto/native. Research therefore runs as regular calls; scoring runs in batch. |
| Cost reporting | `usage.cost` is returned on every response, and `llm.py` logs it. The figures match the observed spend, including the search fees. |
| Search text | `message.annotations[].url_citation.content` contains Exa's crawled page text. We use it as a verification fallback (see below). |

### Exa vs native search (5 members, same prompt v1)

| | Exa | Native |
|---|---|---|
| Statements found | 42 | 66 |
| Verified by live fetch | 30 | 48 |
| No-match (likely fabricated or misquoted) | 2 | 2 |
| Fetch failed (bot-blocked or PDF) | 10 | 16 |
| Cost for 5 people | **$0.56** | **$2.40** |
| Cost per verified quote | $0.019 | $0.050 |
| Projected cost for 620 people | **~$70** | **~$300** (over budget) |

**Decision: keep Exa.** Native finds about 1.6× more, but costs 4.3× as much and doesn't fit the budget. Most of native's extra quotes came from high-profile members (Hawley, Obernolte). Those members already have plenty of CeSIA and X evidence. For low-profile members, the two engines found the same amount.

Exa came in at about $0.11 per person, roughly half the $0.20 the plan assumed.

### Verification

- When the live fetch works, the fuzzy match at ≥ 0.9 is precise. Only 4 of 108 quotes failed on content.
- About 24% of URLs fail to fetch. Most are 403 bot blocks: senate.gov member sites, jec.senate.gov, axios, fastcompany, and others. **We do not circumvent bot protection** (plan rule: no ToS-violating scraping).
- Fallback: if the live fetch fails, match against the page text the search engine (Exa) returned for that URL. It is an independent copy of the source that the model can't edit. These quotes are marked `verified_via: search_text`.
- PDF sources (house.gov statements, congress.gov testimony) are now read with pypdf.

## X API (pay-per-use)

Sources: [pricing](https://docs.x.com/x-api/getting-started/pricing), [post cap](https://docs.x.com/x-api/fundamentals/post-cap), and the [full-archive quickstart](https://docs.x.com/x-api/posts/search/quickstart/full-archive-search).

| Item | Finding |
|---|---|
| Posts read | $0.005 per post returned |
| Counts: All | $0.01 per request |
| Monthly cap | 3M post reads |
| Full-archive search on pay-per-use | Yes (`/2/tweets/search/all`, `max_results` 10–500, 1 req/sec) |
| Deduplication | The same post read again within the same UTC day is not billed twice |
| Bearer token | Works. Tested live. |

**⚠ The plan's counts estimate is wrong.** `counts/all` with `granularity=day` returns **at most 31 days per request**, with a `next_token` for the rest. This was tested live. Covering 2023-01-01 to now takes about 47 requests per person. That works out to about **$0.47 per person, or about $290 for 620 people**, not $6–12. Hour and minute granularity cover even less per page.

Options for Checkpoint 0:
1. **(Recommended) Skip counts and pull directly** with `search/all`. Take the newest 100 posts per person (1 page). The cost is $0.005 × the actual number of posts, and `next_token` tells us whether there are more. Price it on the 20-person dry run first, then extrapolate.
2. Run counts on a random sample of about 30 people (about $14) to estimate the distribution, then pull.
3. Narrow the window to 2025-01-01 onward (about 23 requests per person). That still costs about $140 in counts alone.

## CeSIA

- The data repo (`lennart-finke/governments-on-superintelligence-data`) is code only. The data is the published payload `https://cesia.org/en/data/attention/quotes-data.json`. Version 2.10.0 was generated 2026-09-22 and collected 2026-09-09. License is CC BY 4.0.
- It has 15,246 rows, 4,250 of them US (2022-01-12 → 2026-09-02).
- The member ID comes from the `si` photo URL (`.../congress/225x275/{bioguide}.jpg`). 3,018 US rows map to a bioguide ID, and **2,783 rows map to current members**.
- **314 of 539 current members** have at least 1 row. 171 have at least 5, and 29 have at least 20. The median is 1. Top: Klobuchar 83, Schumer 63, Mace 59, Peters 48, Blackburn 44, Hawley 44.
- The rows carry CeSIA's own judge scores (`sc`) and stance (`st`). We **do not pass these to our scorer**, so it sees no prior labels. We use only the quote, date, URL and context.

## Roster (preview for Phase 1)

- `legislators-current.json` lists 539 members: 100 senators and 439 House members, including delegates.
- 505 of them have a Twitter handle in `legislators-social-media.json`.

## X via emusks (decision 2026-11-05, approved by Harshul)

**Plan change:** X posts are collected for free with [emusks](https://emusks.tiago.zip/). It is an unofficial JS client that calls X's internal web API, logged in with a throwaway account's `auth_token` (`X_AUTH_TOKEN` in `.env`). Harshul explicitly approved overriding the "no ToS-violating scraping" rule for X only. Risks accepted: the throwaway account may be suspended, and the method is unofficial. The paid API is kept only as a fallback.

- Script: `scripts/x_emusks.mjs`. It sends one query per person (same keywords as the plan, `since:2023-01-01 -filter:retweets`) to the "Latest" search tab.
- X's web search stops paginating early. The fix is to **walk backwards in time**: when the cursor dries up, restart with `until:<oldest day seen + 1>`.
- Throttle: 1 request every 20 seconds, about 45 per 15 minutes, under the documented 50 for SearchTimeline. It takes about 12 pages (≈4 minutes) for a heavy poster.
- **Recall test (Obernolte, 2023-01-01 → now):** the paid full-archive API (cost $0.63) found 125 posts and emusks found 120. 118 overlap, **94% recall**. emusks also found 2 posts the paid API didn't.
- Handles must be correct and active. `RepObernolte` didn't resolve, so the roster step must validate each handle (emusks `users.getByUsername`, free).
- X spend so far: $0.70, all on ground-truth checks.

## X: switched to the paid API partway through (2026-11-05, approved by Harshul)

emusks was rate-limited to about 45 searches per 15 minutes, which put the full run at 15+ hours. After the first 132 people, Harshul approved using the paid API for everyone else.
- `scripts/x_paid.py`: the same keyword query on `tweets/search/all` (`-is:retweet`, from 2023-01-01). It writes the same file schema as emusks, with `source: "x_api_full_archive"`.
- Each person is capped at 500 posts (newest first). A capped file has `truncated: true`, so the oldest AI posts of the heaviest posters may be missing.
- Mixed sources: the first 132 people came from emusks (about 94% recall vs. the paid API, from the Obernolte test). Everyone else came from the paid API.
- Handle validation uses the post authors in each file (`phase1_handles_finalize.py`), not a separate lookup.
- Other data-source substitutions: GovTrack ideology comes from the copy in Roe's repo, because govtrack.us sits behind a Cloudflare check. Quote verification falls back to Exa's page text when the source page blocks fetches (`ok_search_text`).
