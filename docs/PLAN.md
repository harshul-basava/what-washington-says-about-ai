# What Washington Says About AI — v2 (simple version)

Plan for Claude Code. Read the whole file first. Do one phase at a time. At each **CHECKPOINT**, stop, report results and spend so far, and wait for Harshul's approval.

## Goal

For each member of Congress, give a clear, evidence-backed read of how they feel about:
1. AI overall (optimistic ↔ concerned)
2. AGI / transformative AI ("AGI-pilled")
3. AI existential / catastrophic risk
4. China / AI race framing
5. AI regulation (pro ↔ anti)

Every score must be backed by verified quotes with links. Also show a simple view of how the volume and topics of AI talk changed over time.

Display it on a simple static site in the style of frontierclock.org. The site is refreshed manually, a few times a year, not continuously.

**Prefer simple.** Add complexity only where it clearly improves the accuracy of per-person sentiment.

## Scope (~620 people)

- All current members: 100 senators and 435 representatives, plus non-voting delegates if easy.
- **New** members-elect from the Nov 3, 2026 midterms who aren't already in Congress (~60–90). Some races are still uncalled as of Nov 5, 2026. Mark `race_called` and add the rest once called.
- **One primary X handle per person**: the most active of official or personal.

## Prior work (for context)

**Roe, "What Washington Says About AGI"** (LessWrong, Jan 2026). Code: `github.com/zroe1/silly-research-sprints/tree/main/politicians_views_ai`.

He used one Sonnet 4.5 web-search call per member asking for "10 quotes", then GPT-4o scored the result 0–100. That design had these problems, which this plan fixes:
- The judge saw the research model's own labels.
- A fixed "10 quotes" request invites padding.
- There was no quote verification.
- Validation was light.

**CeSIA "Politicians on AI"** (`cesia.org/en/data/attention/`; code at `github.com/lennart-finke/governments-on-superintelligence-data`; CC BY 4.0).
- Utterance-level quotes from official US records (Congressional Record, hearings), tagged by 3 LLM judges, with quotes verified verbatim.
- Use it as **free extra evidence** for current members. Attribute it on the site.

## Setup

- Python + `uv`. Secrets are already in `.env` (git-ignored): `OPENROUTER_API_KEY` and `X_BEARER_TOKEN`. Add `.env` to `.gitignore` first thing. Never print, log, or commit keys.
- Provider: **OpenRouter** (OpenAI-compatible API at `https://openrouter.ai/api/v1`).
  - Model: **Claude Sonnet 5.5** (`anthropic/claude-sonnet-5.5`; verify the exact slug in Phase 0) for everything.
  - Research: the `openrouter:web_search` server tool with `engine: "exa"` (~$0.007 per search, up to 10 results) and `max_results ≤ 10`. Cap at ~8 searches per person. In Phase 0, compare Exa with native search on 5 people and keep Exa unless it's clearly worse.
  - Scoring and topic tagging: use a `:batch` model variant if one is available for Sonnet (verify). Otherwise use regular calls; scoring is cheap either way. Use JSON schema / structured outputs.
  - Keep the provider behind one function in `llm.py`, so switching providers later is a one-line change.
  - Read actual cost from OpenRouter's response usage/cost fields and log it.
- Budget: $200 OpenRouter credits (key has a credit limit) and $150 X credits (console spending limit).
- Route every paid call through one helper, `llm.py`. It logs cost to `data/cost_ledger.jsonl` and hard-stops at the budget in `budgets.yaml`.
- Before any paid run over $5, do a **20-person dry run**. Show the outputs and the projected full cost.

## Phases

### Phase 0: Verify and scaffold (~$1)

- Confirm model IDs and prices, and whether `web_search` works inside Batch requests.
- Confirm X API pay-per-use details:
  - As of Nov 5, 2026, per docs.x.com: $0.005 per post returned, $0.01 per counts/all request, and a cap of 3M post reads per month. Full-archive search *is* on pay-per-use. Re-check in the Developer Console.
- Download the CeSIA release. Count US rows per member of Congress.
- Write findings to `docs/assumptions.md` with links.
- **CHECKPOINT 0.**

### Phase 1: Roster

- Source: `unitedstates/congress-legislators` (`legislators-current.yaml` and `legislators-social-media.yaml`) for current members.
- Members-elect come from called 2026 results (AP / official), with handles taken from campaign sites. Note that the unitedstates repo is updated after the Jan 3, 2027 swearing-in.
- Fields: `bioguide_id` (or a temporary ID for members-elect), name, chamber, state/district, party, status (`current` / `member_elect`), primary X handle, ideology score (GovTrack, where available).
- Write uncertain handles to `handle_review.csv` for Harshul.
- **CHECKPOINT 1.**

### Phase 2: Gather evidence per person

For each person, build one `evidence/{id}.json` containing a list of statements. Each statement has: text, date, source_type (`floor` / `hearing` / `x` / `web`), url, and verified (bool).

1. **Official records (free)**: CeSIA US quotes mapped to the member.
2. **X**, via full-archive search. This was verified on Nov 5, 2026: `GET /2/tweets/search/all` is available on pay-per-use and is billed $0.005 per post returned.
   - Query per person (include all of their handles; billing is per *matching* post, so extra handles are cheap):
     `(from:H1 OR from:H2) (AI OR "artificial intelligence" OR AGI OR superintelligence OR OpenAI OR Anthropic OR ChatGPT OR deepfake OR "machine learning" OR chatbot) -is:retweet`, with `start_time=2023-01-01`, `max_results=500`. Queries can be up to 1,024 characters.
   - **Step 1, price it first.** Call the counts endpoint (`/2/tweets/counts/all`, $0.01 per request) with the same query for every person. That costs about $6–12 total and gives the exact number of matching posts, so the cost is known before pulling anything.
   - Report the projected cost at the checkpoint. If it's over $150, cap posts per person at the most recent ~100, or narrow the keywords. Spot-check for noise, e.g. "AI" matching unrelated acronyms.
   - Set a spending limit in the X Developer Console as a backstop.
3. **Web research** (Sonnet 5.5 via OpenRouter + web_search, max ~8 searches per person):
   - Prompt: find **all** substantive public statements by this person about AI (interviews, press releases, op-eds, campaign site, debates, podcasts, posts), with exact quote + URL + date. **Returning zero is fine.** Never request a fixed number.
   - Then fetch each URL and check the quote appears (fuzzy match ≥ 0.9). Mark it `verified`; drop anything that fails.
   - Expected cost: ~$0.20 per person → **~$130**.
4. Deduplicate statements across sources.

**CHECKPOINT 2.** Report per-person statement counts, the share verified, and spend.

### Phase 3: Score each person

- One scoring call per person (Sonnet 5.5 via OpenRouter). The input is **only** the verified statements (text, date, source). There are no prior labels.
- The output, via JSON schema, contains for each of the 5 dimensions:
  - a **score on a 0–4 scale** with written anchors and 1–2 example quotes per level in `rubric.md`, or `insufficient_evidence`
  - a 1–2 sentence justification
  - the IDs of the statements it relied on
- It also outputs a 2–3 sentence plain-English summary of their AI views, and an `evidence_strength` value (low / medium / high).
- **Consistency check (cheap)**: run the scoring twice, with statements shuffled. Where the two runs differ by ≥2 on any dimension, flag the person for manual review. Average otherwise.
- Tag each statement with 1–3 topics from a short fixed list for the over-time chart: jobs/economy, China/competition, national security, kids/online safety, deepfakes/elections, copyright, energy/data centers, regulation, AGI/transformative, x-risk/loss of control, misuse (bio/cyber), other. Do this in the same batch call as scoring where possible.
- Cost: **~$10–25**.

### Phase 4: Sanity check

- Harshul reviews ~40 people: the top 15 by x-risk, the top 10 by AGI-pilled, 10 random, and all flagged people.
- Compare against Roe's scores (`progress.json`) and note big disagreements.
- Fix the rubric if needed, and re-score (cheap).
- **CHECKPOINT 4.**

### Phase 5: Website (frontierclock-level simplicity)

A static site (Next.js static export or plain HTML + Observable Plot/Chart.js) on Vercel, reading from small JSON files. Sections:

1. **Header**: one-line question, short framing, "last updated" date.
2. **Explore**:
   - AI statements per quarter, stacked by topic, with a party filter.
   - Ideology vs. a selected dimension (scatter), with hover showing name and summary.
3. **Members**: a sortable/searchable table with name, party-state, chamber, the 5 scores (or "—" when there is insufficient evidence), evidence strength, and a "new member" badge. Clicking a row shows the summary and verified quotes with links.
4. **Method**: a short numbered list, plus caveats:
   - Public statements are not the same as beliefs or votes.
   - LLM-scored, with human spot-checks.
   - Official records lag.
   - X coverage limits.
   Also credit CeSIA, the unitedstates project, and GovTrack.
5. **Footer**: GitHub, CSV download, contact.

To refresh, run `make refresh` manually. It re-runs Phases 2–3 for everyone, or only for new and changed people. Plan for roughly one refresh after the new Congress is seated (Jan 2027) and then quarterly at most.

### Phase 6: Write-up support

- A notebook that produces the figures and headline numbers for the LessWrong post.
- Draft bullet findings for Harshul to edit.

## Budget (USD; confirm in Phase 0)

| Item | Estimate |
|---|---|
| Web research, ~620 people × ~$0.20 | ~$130 |
| X (capped) | $50–150 |
| Scoring ×2 + topic tags | $10–25 |
| Dry runs, reruns, buffer | ~$50 |
| Hosting, CeSIA data, congress-legislators | $0 |
| **Total, first build** | **≈ $230–350** ($200 OpenRouter + up to $150 X) |
| **Each later refresh** | **≈ $50–150** (only new or changed people get re-researched) |

## Rules for Claude Code

- Phases in order. Stop at checkpoints.
- Prompts and rubrics live as files in `config/`, not inline. Record the rubric version on every score.
- Keep the raw evidence and every source URL. Every quote shown on the site must be `verified`.
- No ToS-violating scraping. Respect rate limits.
- If something here is wrong or there's a simpler way, say so at the next checkpoint.
