# Federal Collection Cost and Speed Strategy

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans after the user authorizes execution. This document does not authorize a run.

**Goal:** Reduce elapsed time and cost per useful federal source while preserving verification, judgment rules, and coverage of priority officials.

**Architecture:** Retrieve official archives once, reuse valid work, and search individual gaps afterward. Process independent work concurrently. Complete collection for a profile before its expensive profile review, then publish a fully checked wave.

**Tech Stack:** Existing Python collectors, OpenRouter models, official X API, GitHub Actions, and static site.

**Spec:** The user's November 12 request: create a strategy for maximum speed and minimum cost with equivalent quality; do not run it yet. Existing behavior appears in `docs/federal-archive-collection.md`, `docs/federal-efficient-collection.md`, and the current rubrics.

## Status and constraints

- The original request paused execution while this proposal was prepared. The user subsequently authorized resuming the existing campaign with its remaining $98.83. Execution retains the original $100 cumulative baseline. Unchecked recommendations below are not claims of completed implementation.
- Keep the existing 500-person eligible roster. Keep institutions separate from people.
- Keep exact quotations, source attribution, publication-date checks, role checks, and duplicate checks.
- Keep the current three DeepSeek label passes, required Sol/Astra escalation, regulation judgments, and independent Astra profile review.
- Keep named-policy review at its current confidence threshold of 0.80. Model confidence does not establish measured accuracy.
- Keep the five scores, 23 regulation categories, summaries, topics, and histories.
- Preserve all campaign spending baselines, provider limits, and daily/monthly limits. A restart does not create a new allowance.
- Preserve the user's separate local review tool and unrelated edits.

## Evidence behind the proposal

The completed archive pilot added 181 excerpts from 23 speeches by five Federal Reserve officials. Its total cost was $2.603508.

| Stage | Recorded cost |
|---|---:|
| Archive extraction | $0.078488 |
| Scores, regulation categories, and summaries | $0.637263 |
| Named-policy judgments | $0.000202 |
| Independent Astra review and context requests | $1.887555 |

Collection accounted for about 3% of this pilot's cost. Repeated profile reviews and repeated context can therefore cost more than extraction. These results do not predict the yield of intelligence agencies or other departments. Excerpts from one speech are also not independent sources.

The checkout already contains archive workers, persistent caches, a cumulative campaign budget, and deferred site builds. Some source-context and verification corrections remain local. Inventory existing behavior before implementation; do not rebuild it or repeat completed research.

## Recommended sequence

### 1. Freeze the work and budget before any restart

**Files:** `scripts/federal_collection_campaign.py`, `config/federal_collection_campaign.json`, campaign reports, and the cost ledger.

- [ ] Reconcile completed requests, uncertain charges, saved evidence, and interrupted reviews from the earlier job.
- [ ] Check current account credit and every applicable cap without a model request.
- [ ] Use the lowest remaining applicable allowance. Retain the campaign's original model and X baselines.
- [ ] Create a fixed queue that records each source, profile, stage, cost, and completion state.

The existing campaign ceilings are $100 for models, $20 for collection within that amount, and a separate $5 for X. These are cumulative ceilings, not fresh money. Do not spend the full allowance merely because it exists.

Before further collection, reserve funds for all pending judgments and context requests. Estimate that reserve from the measured cost of comparable profiles, with a 50% planning margin and the existing $20 minimum. Use maximum-request reservations for actual concurrent calls. An estimate does not guarantee enough money; stop new collection if the review reserve becomes inadequate.

**Acceptance:** A restart retains earlier spending and pending work. Insufficient credit stops new requests before they launch.

### 2. Collect documents first and individual gaps second

**Files:** `config/federal_archives.json`, `federal_archives.py`, `scripts/daily/federal_sources.py`, and the campaign runner.

- [ ] Retrieve official speech archives, testimony, hearing transcripts, press remarks, and prepared statements once per canonical source.
- [ ] Extract all eligible speakers from a source together, with separate attribution for each speaker.
- [ ] Use source-specific, reviewed speaker mappings for multi-speaker hearings. A nearby name is insufficient.
- [ ] Search individual officials only when the archive pass leaves material gaps.
- [ ] Use official X searches for verified accounts with unresolved gaps. Resume saved time intervals and cursors.

Rotate across agency groups. Within each group, prioritize influential officials with little evidence. Preserve a dedicated queue for difficult groups such as CIA, NSA, and CISA. High-volume speech archives must not consume the full budget.

Track distinct sources, newly covered officials, and agency coverage alongside excerpt counts. Preserve source references when repeated text appears elsewhere. Do not increase counts by splitting one passage into redundant excerpts.

**Acceptance:** The queue reaches every target agency before another full cycle. Blocked pages and unsearched profiles remain visible as gaps.

### 3. Reuse every compatible result

**Interfaces:** `Client.search`, `Client.extract`, `extraction_signature`, and `collect` in the existing collectors.

- [ ] Reuse source snapshots and completed extraction responses when their inputs remain unchanged.
- [ ] Include source content, subject identity, attribution, model, prompt, rubric, and relevant date windows in the appropriate cache keys.
- [ ] Retain empty results and rejected candidates, with bounded retry dates or explicit invalidation rules.
- [ ] Retry transient failures with bounded backoff. A blocked page is not a completed empty search.
- [ ] Share durable caches between historical and daily workflows.

An unchanged statement keeps its valid labels. A changed quote, attribution, rubric, model, or prompt invalidates the affected result. A growing evidence set invalidates the relevant profile summaries and reviews. Changed source-context rules invalidate only affected extractions.

**Acceptance:** Replaying identical inputs makes zero paid calls. Changed inputs trigger the affected work only. Interrupted outputs never count as complete.

### 4. Use bounded parallel work and one final profile review

**Files:** `federal_archives.py`, `federal_analysis_models.py`, `scripts/federal_expansion_runner.py`, and workflow configuration.

- [ ] Start from the existing ceilings: eight document fetches, four extraction or DeepSeek calls, and two expensive review calls per applicable stage.
- [ ] Make all concurrent requests share the same reservations and spend ledger.
- [ ] Serialize evidence writes and checkpoint updates.
- [ ] Run statement analysis while other independent profiles collect evidence, if the existing dependencies permit it.
- [ ] Complete each profile's planned collection wave before its final regulation summary and independent Astra review.
- [ ] Include each full source context once per request, with explicit references from its excerpts.
- [ ] Build the site once per completed publication wave.

Do not shorten source context or substitute a cheaper model without a separate quality comparison. Keep independent passes independent. Reuse an Astra review only when its complete input and review configuration remain unchanged.

Tune worker counts only after observing throughput, timeouts, rate limits, and reserved cost. Higher concurrency can reduce elapsed time; it does not itself reduce API charges. Account for the aggregate number of calls across stages.

**Acceptance:** Fixed-response fixtures produce the same accepted evidence and scores with serial and parallel execution. Retries cannot duplicate records or exceed the budget.

### 5. Check quality and missed evidence before expansion

**Files:** Existing collector and campaign tests, source verification reports, and the internal review interface.

- [ ] Reuse completed pilot evidence and cached responses for offline comparisons.
- [ ] Compare accepted and rejected records against the existing verifier on a fixed source set.
- [ ] Include speeches, testimony, X posts, joint statements, ambiguous speakers, conditional language, partial dates, and changed roles.
- [ ] Check full documents for missed relevant passages. Reviewing only accepted excerpts cannot measure collection recall.
- [ ] Use a small, diverse live comparison only if a proposed change remains untested. Limit its additional spend to at most $3 within the remaining campaign allowance.
- [ ] Stop expansion for a new attribution, quote, date, role, or stance error. Investigate any lost relevant passage.

Proposed human review: 100 randomly selected new records, plus 50 deliberately selected edge cases. Keep the two samples separate. Spread the edge cases across source types and difficult agency groups. Include source-level checks for omissions.

With zero errors in 100 independent random records, the approximate one-sided 95% upper bound is 3% for the sampled error type. Shared sources reduce independence. Deliberately chosen edge cases do not support a population error estimate. This sample is a practical check, not proof of equal accuracy.

Preserve the existing review rules immediately. Claim equivalent observed quality only after comparison. Do not claim equivalent coverage from a high excerpt count alone.

**Acceptance:** All additions pass automated source replay. The comparison identifies no new critical errors or unexplained losses. Pending human concerns remain visible.

### 6. Publish complete waves and report useful yield

**Interfaces:** `verify_sources(root, audit)`, the existing analysis builders, and campaign completion checks.

- [ ] Verify every new excerpt against its retained source and attribution metadata.
- [ ] Complete all required labels, summaries, named-policy judgments, and Astra reviews for the publication wave.
- [ ] Report model cost, X cost, unique sources, newly covered officials, agency coverage, and unresolved gaps.
- [ ] Measure elapsed time and cost per verified source and newly covered official, as well as per excerpt.
- [ ] Publish only after the required checks pass. Keep incomplete research and unresolved judgments explicit.
- [ ] Apply the same cache, reservation, and incremental-review rules to daily updates.

## Expected benefit and uncertainty

The safest savings come from avoiding repeated searches, downloads, context, and reviews. Parallel requests reduce idle time. Local filtering can reduce CPU work if exact matching still decides acceptance.

No defensible whole-run speed multiplier or dollar total exists yet for the remaining agency mix. The Federal Reserve pilot provides a demonstrated low-cost source pattern, not a federal-wide forecast. Use the next authorized, bounded comparison to estimate completion time and total review cost before expansion.

## Review focus

1. An interrupted request can incur a charge without a valid output; reconcile it before retrying.
2. A joint or institutional statement must not become a personal stance through a name match.
3. Empty caches must not conceal new documents, corrected parsers, or changed source rules.
4. Large archives must not crowd out influential officials with sparse evidence.
5. A reviewed sample can look accurate while collection misses contrary evidence; include full-source checks.

**Execution status:** The user authorized the existing campaign to resume on November 12. Its implementation ledger is `.superpowers/sdd/2026-11-12-federal-efficient-collection/progress.md`. Collection and required reviews remain subject to the original cumulative limits and verification gates.
