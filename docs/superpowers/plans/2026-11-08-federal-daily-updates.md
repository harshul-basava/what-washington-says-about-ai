# Federal Daily Updates Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. Track the steps below.

**Goal:** Update the existing executive and institution profiles daily, using verified public evidence and the existing DeepSeek/Astra policy cascade.

**Architecture:** Add an independent federal collector to the daily runner. Search four configured source groups, verify and append excerpts, persist retries, assess only executive candidates, and rebuild the shared site. Keep federal evidence separate from the congressional five-score labeling log.

**Tech Stack:** Python 3.12, httpx, the existing paid-call gateway, unittest, GitHub Actions.

**Spec:** The user's request in this chat: automate executive branch, NSA, Commerce, and Superintelligence Task Force updates daily like Congress; explain the initial search depth.

## Global Constraints

- Reuse the existing 11:00 UTC schedule and current branch. Do not merge or activate a second schedule on the fork.
- Keep existing evidence IDs and judgments. Only append exact verified excerpts with explicit attribution.
- Use the configured DeepSeek V4.1 Flash 1017 and Astra models. Review confidence below 0.80 through the existing cascade.
- Tag every scheduled paid call with `daily_`; honor shared lifetime/monthly caps and separate $0.50 collection / $2.00 judgment run limits.
- Search the four groups with bounded official-domain and reporting-domain queries. Start with 14 days, overlap successful searches by three days. Persist discovered pages before extraction; retry failures and page-limit overflow.
- Keep institution statements separate from individual statements. Never infer membership changes or assign the DOJ task force's statements to the White House task force.
- Dry runs make no network calls or writes. Missing keys and failures remain visible. Federal work runs even if Congress fails.

## Review Focus

- Publisher/domain boundaries and explicit attribution, including unnamed collective statements and similarly named task forces.
- Retry recovery after extraction, append, search, or budget failure; no skipped backlog or reassigned IDs.
- Date uncertainty and changed pages; search dates do not become statement dates.
- Monthly budget reservations across both model stages and collection; federal statements never enter congressional scoring.
- Scheduled invocation, source selection, offline dry run, and publication after partial failure.

### Task 1: Collect federal evidence

**Files:** `config/federal_sources.json`, `scripts/daily/federal.py`, `scripts/daily/federal_sources.py`, `tests/test_federal_daily.py`.
**Interfaces:** `collect(root, config, since=None, dry=False) -> report`; exact verification and append helpers; separate state and status under `data/`.

- [x] Add tests for exact quote/attribution/date checks, domain boundaries, stable IDs, pending retries, failure checkpoints, changed content, and no-write dry runs. Run and observe failure.
- [x] Implement source groups, paid search and extraction, exact verification, persistent page queue, safe append, and source audit records.
- [x] Run `uv run python -m unittest discover -s tests -p test_federal_daily.py -v`. Expected: all pass.

### Task 2: Connect judgments and the daily job

**Files:** `scripts/phase3_policies.py`, `scripts/daily/run.py`, `.github/workflows/daily.yml`, `Makefile`, policy runner and daily integration tests.
**Interfaces:** policy runner `--scope executive --daily`; federal runner CLI; daily `--sources federal`.

- [x] Add tests for executive-only selection, monthly reservations/tags, independent collection/label failures, daily routing, and congressional isolation. Run and observe failure.
- [x] Add routing, resumable federal judgments, site build, status reports, workflow summary, and federal-only commands.
- [x] Run `make test` and an offline federal dry run. Expected: passing tests; no paid calls or writes from the dry run.

### Task 3: Verify and deliver

**Files:** README, prompt catalog, source coverage notes, plan execution record.

- [x] Document source scope, limits, retry behavior, command usage, schedule activation conditions, and the measured initial coverage.
- [x] Run a bounded live federal collection and judgment smoke test, inspect attribution, and rebuild the site. Preserve operational failures in the status report.
- [x] Run the full suite and shared build, then request one fresh independent review. Resolve material findings with regression tests.
- [ ] Commit and push to the existing feature branch; check PR compatibility and GitHub deployment status.

## Execution Record

- Initial audit: 21 profiles (13 people, eight institutions), 27 excerpts from 16 distinct URLs; source manifest lists 21 pages, including role sources. Dates: 15 excerpts from 2026, nine from 2025, one from 2024, two undated. Sixteen excerpts used direct retrieval; eleven used retrieved search text. This was a narrow manual seed, not an exhaustive survey.
- Implementation choice: source and membership registry edits remain manual. Daily automation updates evidence and judgments for registered subjects. Search coverage cannot establish completeness.
- Preflight: current branch is clean at 095aff5. Existing daily script collects Congress only; its log feeds congressional scoring. Federal evidence therefore needs a separate append log and state.

- Collector tests failed before implementation, then passed. The tests cover stable IDs, exact source checks, source boundaries, retry queues, chunk resume, failed search checkpoints, no-write dry runs, and congressional isolation.
- Integration tests failed before implementation, then passed. Daily calls reserve against the monthly cap; executive scope excludes Congress; either pipeline can fail while the other still runs. Federal work now runs first to avoid a long congressional run consuming its job window.
- Fresh independent Astra review found four material issues: an Astra reservation larger than the initial $0.50 cap; missing canonical institution aliases; invented day-one precision from month-only anchors; and confusion between the two task forces. All four received regression coverage and fixes. The default judgment cap is now $2.00, while the shared monthly cap stays unchanged.
- Additional regression tests cover unchanged discovery results consuming the page quota and provider prose before fenced JSON. The fixed parser requests JSON output and accepts exactly one fenced result.
- The reviewer declined to certify live search completeness, final live evidence, or deployment. The coordinator owns these checks. Search completeness is explicitly outside the promise: the collector searches configured domains for registered subjects. Role and membership additions remain manual.
- The first live pilot used the initial code. It completed all eight searches and saved evidence and queued pages. It was interrupted after the review fixes to resume with the corrected parser and validators. The second live pilot limits extraction to two pages per group; the scheduled default remains six.

- Final verification: 58 Python tests and 19 JavaScript tests pass. The shared site build passes (649 congressional members, ten policies). The offline federal dry run shows zero pending model pairs and makes no writes or network calls. The browser shows the partial update date and queue counts in the institution view.
- Live verification added 12 distinct excerpts from seven source URLs. Four new statement-policy pairs received accepted DeepSeek judgments; no model calls remain pending. One pre-existing federal case still needs human review. The two live pilots cost $0.1852 in recorded calls. The interrupted request may have incurred unreported provider cost.
- Live collection remains partial by design: 61 pages remain queued after the bounded pilot, including two pages with rejected extraction rows. The scheduled default checks six pages per group. The pilot checked two. The saved status report discloses both the backlog and errors.
- Manual source review found an exact dated quote repeated on an NSA index and its release page. The unpublished duplicate was removed, and a failing regression test now verifies deduplication across URLs. All original published evidence IDs remain unchanged.
- All 2,484 pre-existing judgment records are identical. The congressional roster, scores, daily labels, daily statement log, and member export are byte-identical. Upstream master remains 13d73ca; no new upstream commits need integration.
- No review findings remain deferred. Roles and membership changes remain manual, and the source search remains bounded. The federal schedule activates when this branch merges into the default branch.
