# Federal X Search Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, then request one independent code review.

**Goal:** Use the user's selected emusks client for federal historical X search and daily updates.

**Architecture:** A small Node worker uses emusks for read-only account lookup and Latest search. A Python coordinator validates sourced account mappings, schedules monthly historical windows and overlapping daily windows, verifies authors and dates, appends evidence, and saves resumable checkpoints. Existing DeepSeek/Astra judgments consume the resulting federal evidence.

**Tech Stack:** Python 3.12, Node 22, locked emusks 2.3.20, unittest and node:test.

**Spec:** The user selected https://emusks.tiago.zip/ and explicitly requested completion without a live search. Earlier instructions authorize federal historical collection, daily integration, the site, and the existing PR.

## Global Constraints

- No live authenticated X search in this turn. No token exists locally. Do not scrape browser credentials or print secrets.
- Reuse the existing branch and pinned dependency. Preserve all existing evidence and judgment IDs; do not change congressional collection.
- Only sourced account mappings can supply evidence. Account owners, institution profiles, and official-role date intervals remain distinct.
- Account lookup must bind returned post author IDs to the sourced handle; pin the resolved user ID and reject a later mismatch.
- Only the author's own post text enters evidence. Reject reposts, promoted posts, mismatched authors, invalid/future dates, and posts outside the query/role interval.
- Retain at most 25 verbatim words per X post URL across federal profiles. Keep full source responses only in ignored local storage.
- Use monthly historical windows from 2023, pagination, a 20-second minimum search interval, a per-run page/time cap, and persisted rate-limit cooldowns. Never rotate accounts to evade limits.
- An empty result does not prove complete archival coverage. Missing authentication and unmapped profiles must remain visible.
- No budget changes or paid model runs are necessary without new evidence. Schedule activation still requires merging the PR.

## Review Focus

- A shared office handle must not attribute another officeholder's posts to the current person.
- Failed, truncated, repeated-cursor, or malformed pages must not advance the successful date checkpoint.
- Evidence append and queue checkpoint interruption must be idempotent.
- Missing credentials must not stop web collection, judgments, or Congress; dry runs make no network calls or writes.
- Credentials and provider error bodies must not enter public state, exports, or logs.

### Task 1: Read-only worker and source registry

**Files:** `scripts/federal_x_worker.mjs`, `config/federal_x.json`, `tests/federal_x_worker.test.cjs`.
**Interfaces:** Worker consumes one JSON object on stdin (`handle`, `query`, `cursor`); returns a minimal public account and normalized posts, or a fixed error code.
- [x] Write failing tests for own-text normalization, author IDs, repost flags, malformed responses, and error redaction.
- [x] Implement a bounded worker with environment-only authentication, safe JSON output, timeout and client cleanup.
- [x] Add source-verified seed mappings and explicit unmapped-profile coverage; verify the tests pass.

### Task 2: Historical and daily collection

**Files:** `scripts/federal_x.py`, `tests/test_federal_x.py`, `scripts/daily/federal.py`.
**Interfaces:** `collect(root, mode='daily', since=None, dry=False, client=None)` returns structured coverage, errors and additions. CLI supports `plan`, `collect`, `--mode historical`, `--ids`, and bounded page limits.
- [x] Write failing tests for date/author verification, role windows, monthly jobs, partial pagination, resume, deduplication, authentication and rate limits.
- [x] Implement the coordinator and atomic state/audit files. Use the existing federal evidence append function.
- [x] Add X as an independent stage before policy judgments; preserve existing failure isolation.
- [x] Run the focused and full suites.

### Task 3: Workflow, site and delivery

**Files:** `.github/workflows/daily.yml`, `.env.example`, `Makefile`, `federal_coverage.py`, `policy_judgments.py`, `site/policies.js`, README and coverage docs.
- [x] Configure Node and npm dependencies plus the optional `X_AUTH_TOKEN` GitHub secret in the daily workflow.
- [x] Add offline plans and historical commands; show mapped accounts, imported post counts, and actual X collection status on the site.
- [x] Run the missing-token path, offline plan, full tests and site build. Do not claim a live search passed.
- [x] Request independent review and fix material findings.
- [ ] Push the existing PR and check conflicts.

## Execution Record

- Baseline f8fbfa4; 186 federal profiles and zero direct X-source excerpts. Existing legacy emusks collector is congressional, skips completed files, and lacks daily checkpoints.
- User explicitly chose integration without a live search after the missing-token check. The current emusks documentation requires an authenticated session for SearchTimeline; guest search is unavailable.
- Native implementation and the current checkout follow the already authorized workflow. No additional design approval is needed for this specified provider integration.

- Independent review found three checkpoint/error issues. Regression tests reproduced each issue before its fix. The second review found no remaining material issues.
- Final verification: 99 Python tests and 26 JavaScript tests passed. The full offline site build passed. The temporary-build test now copies the shared X configuration module.
- Missing-token checks made no X requests, imported no posts, and wrote only the explicit unavailable status. The offline historical plan contains 945 monthly windows for 23 accounts across 21 profiles.
- The browser rendered the new federal coverage text: 23 sourced accounts, 21 mapped profiles, zero X excerpts, and authentication required. The local preview runs at http://127.0.0.1:8765/.
- All existing evidence, judgment caches, scores, congressional member exports, and policy member exports remain byte-identical to the baseline. Account mappings and coverage documentation identify 165 unmapped federal profiles.
- Fetched origin/master at f4c83e6; it is an ancestor of this branch. No merge with the default branch is required.
