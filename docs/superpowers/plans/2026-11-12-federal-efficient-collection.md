# Efficient Federal Collection Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan inline. Preserve the existing internal review-tool changes.

**Goal:** Apply the approved bulk collection strategy to current federal officials, run a guarded trial and broader campaign within the new credit, and push verified evidence and judgments.

**Architecture:** Extend the existing archive inventory and collectors. Use bounded parallel downloads/extraction with serialized evidence writes, persistent query/source caches, agency-fair queues, and a cumulative campaign budget. Reuse existing judgment inputs and outputs; finish reviews before declaring a campaign complete.

**Tech Stack:** Existing Python, httpx, standard-library concurrency, OpenRouter, official X API, GitHub Actions, static site.

**Spec:** The seven-point strategy approved in this chat: bulk official documents; permanent work records; reuse unchanged judgments; lossless context; concurrent independent work; agency-aware allocation; offline verification and a $3 trial before expansion.

## Global Constraints

- Current eligible roster only; no private or former officials added.
- Keep exact quotes, source attribution, date/role checks, duplicate suppression, three DeepSeek label passes, Sol/Astra escalation, and independent Astra stance audits.
- Read-only credit check first. At 2026-11-12 06:40 UTC: account $123.272538; workspace $119.483081 remaining; repository $45.873511 remaining. Raise repository lifetime ceiling from $500 to $600 under the user's new budget authorization. Campaign maximum $100; trial maximum $3 within that ceiling. No provider cap or daily/monthly cap changes.
- Extraction/discovery maximum $20 within the campaign; reserve the rest for judgments and context. Stop collection before review funds run out. X remains under its separate existing caps; any campaign X use gets an additional fixed cumulative ceiling.
- No repeated paid work when source/query/model/prompt/subject inputs are unchanged. Rejections and empty results remain cached and visible.
- Preserve the local human review tool. Push only scoped code and public evidence. Full raw documents, responses and secrets stay out of Git.

## Review Focus

- Concurrent requests must share reservations and cannot overspend after a restart.
- Parallel document processing must not overwrite evidence or checkpoints.
- Cached empty results must invalidate for a changed source, query window, model or subject.
- A high-volume agency must not starve low-evidence priority officials.
- Failed reviews and blocked sources must remain visible; no false completion or missing-evidence-as-stance.

### Task 1: Concurrent, fair archive collection

**Files:** `federal_archives.py`, `tests/test_federal_archives.py`, `config/federal_archives.json`.
**Interfaces:** Extend `collect(..., fetch_workers=1, extraction_workers=1)` without breaking the daily caller. Use one shared extraction client and serialize evidence appends. Return per-document and per-agency outcomes.

- [x] Write failing tests for concurrent shared-subject appends, total chunk limits, cache reuse and fair source ordering.
- [x] Implement bounded concurrency, persistent checkpoints, agency-fair selection and expanded official indexes.
- [x] Run archive tests and compare serial/parallel accepted evidence on fixed fixtures.
- [x] Commit the tested collector.

### Task 2: Persistent search reuse and deferred builds

**Files:** `scripts/daily/federal_sources.py`, `federal_analysis_models.py`, `scripts/federal_expansion_runner.py`, focused tests.
**Interfaces:** Cache `Client.search` by complete request inputs and daily check date; save raw responses before parsing. Add optional build deferral without changing defaults or analysis semantics. Allow a per-stage review worker ceiling.

- [x] Write failing tests for repeated/empty searches, invalidation, interrupted responses and unchanged judgment reuse.
- [x] Implement persistent search cache, four extraction/DeepSeek workers and two high-cost review workers; defer redundant intermediate exports.
- [x] Run the affected suites and commit.

### Task 3: Cumulative campaign and daily integration

**Files:** new `scripts/federal_collection_campaign.py`, campaign config/workflow, `budgets.yaml`, daily cache configuration, tests.
**Interfaces:** `plan`, `run`, and `verify` commands. Durable campaign baseline, trial gate, source queue, evidence-ID baseline, stage checkpoints, per-agency yield and cost report. Resume existing work; never reset allowances. Use existing policy and Astra pipelines. Discover individual sources only for gaps after archive work.

- [x] Write failing tests for budget persistence, review reserve, trial gate, added-evidence recovery and truthful terminal states.
- [x] Implement the runner, guarded workflow, current-roster gap search and capped X fallback where existing verified accounts need it.
- [x] Add the new caches to daily/pilot workflows and use the same daily concurrency group.
- [x] Run full offline tests, obtain an independent code review, fix important findings and push.

### Task 4: Trial, expansion and publication

**Files:** campaign reports, evidence, judgments, site exports, documentation.

- [x] Recheck credit after the repository ceiling update; replay cached evidence offline.
- [x] Run the $3 trial across agency groups. Verify sources and complete judgments before broad expansion.
- [x] Continue the campaign under its original $100 baseline; inspect each stage and fix failures without lowering verification rules.
- [x] Verify every addition against retained source snapshots, check independent primary-source samples, and confirm all required judgments finish.
- [x] Build once per completed publication wave; push evidence/results and verify the dev site and remote commit.
- [x] Report total cost, unique sources, officials/agencies reached, remaining gaps and unused budget. Complete the goal only after this audit passes.
