# Federal Roster and Historical Research Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for code. Independent roster research follows superpowers:dispatching-parallel-agents.

**Goal:** Expand federal coverage across the requested policy groups, research every registered person historically, and include the expanded roster in daily collection.

**Architecture:** Verify the roster from primary role sources and dated reporting. Add a resumable per-subject historical research pipeline, using the congressional research model and eight separate web search passes. Reuse exact evidence verification and the existing policy cascade. Derive named daily queries from the registry and expose research coverage and gaps on the site.

**Tech Stack:** Python 3.12, httpx, pypdf, unittest, the existing OpenRouter gateway and static site.

**Spec:** The user's instruction in this chat authorizes all groups discussed: White House, Commerce, national security, other policy agencies, task forces, and former officials. It requests historical depth comparable to Congress and daily inclusion.

## Global Constraints

- Reuse the current checkout and PR #2; preserve published evidence IDs, existing judgments and congressional scores.
- Include only sourced roles. Separate current/documented, historical, and reported adviser memberships. Do not infer a current appointment from an old source.
- Define inclusion by direct AI policy responsibilities, export controls, evaluation, national security, procurement or regulation. Include relevant former officials serving since 2023.
- Use the same Sonnet 5.5 research model as Congress, with source and time diversity. Use DeepSeek V4.1 Flash 1017 policy judgments and independent Astra review below 0.80.
- Do not fabricate quotes to reach a number. Compare people separately from institutions. Congress currently has a median of 12 statements per person; disclose remaining gaps.
- Historical research uses the existing lifetime budget and a per-run reservation cap. Daily collection retains monthly caps and daily tags. Do not increase budgets.yaml.
- X archive and govinfo keys are absent locally. Search public pages, transcripts and indexed posts; explicitly report missing API-backed channels.
- Check official-role attribution, date precision, duplicate excerpts and source text. Preserve unknown dates. Do not copy collective statements into every member profile.
- Do not publish full source pages. Store local raw research in ignored data/raw; publish only audit metadata and verified excerpts. Limit new non-government-source quotations to 25 words per URL.

## Review Focus

- Dates and roles across administration changes, including officials who left during 2026.
- Exact attribution in long speeches, PDF testimony and collective statements; source retrieval is independent of generated quotes.
- Restart recovery, model-output failure, source failure, duplicate and overlapping statements, and concurrency budgets.
- Every registered person receives a named daily search assignment, including historical profiles; budget failures cannot silently remove a group.
- Research-completed status never implies exhaustive evidence or API-backed X coverage; reported site metrics must match tracked data.

### Task 1: Verified roster

**Files:** `config/policy_subjects.json`, `config/federal_research_seeds.json`, new empty evidence files, `docs/federal-roster-sources.md`.
- [x] Integrate independent White House, Commerce/economy and security/agencies research fragments after schema, duplicate and role-source checks.
- [x] Ensure every requested group has relevant people and institution profiles. Preserve original IDs and quotes.
- [x] Validate the full registry with `policy_subjects.load_subjects` and `load_evidence`; expected: no errors.

### Task 2: Historical research

**Files:** `scripts/federal_research.py`, `config/federal_research_prompt.md`, `config/federal_research.json`, shared federal source helpers, `tests/test_federal_research.py`.
- [x] Write failing tests for independent source verification, document-author attribution, date precision, PDF extraction, checkpoint resume, spending reservations and source quotation limits.
- [x] Implement `research` and offline `plan/report` commands with per-person audit records, raw local caching, source seeds, coverage metrics and gap-focused follow-up passes.
- [x] Run tests; expected: all pass, with malformed or unsupported evidence excluded and reported.
- [x] Run historical research for every registered person and institution. Run follow-up searches for thin profiles and record public-evidence gaps.

### Task 3: Daily inclusion and site coverage

**Files:** `scripts/daily/federal.py`, `config/federal_sources.json`, `policy_judgments.py`, `site/policies.js`, tests, README and prompt catalog.
- [x] Write failing tests for complete daily group assignment, named queries, fair retry order, scope isolation and research metrics.
- [x] Add all source groups, derive batched named queries from registered profiles, filter extraction to source-named subjects and preserve safe retries.
- [x] Show historical search status and evidence depth on profiles, plus a downloadable coverage report. Keep public model confidence distinct from search completeness.
- [x] Run the full suite, offline daily plan and site build; expected: passing checks with all profiles assigned.

### Task 4: Judgment, review and delivery

- [x] Assess every new policy candidate through the confidence cascade, retry incomplete model output, and retain human-review cases.
- [x] Inspect live sample evidence and source diversity; compare per-person depth with Congress. Report missing channels and unresolved low-evidence profiles.
- [x] Request one independent final code review, fix material findings with regression tests, run the full suite and inspect the browser.
- [ ] Commit and push the existing PR, update its description, and check compatibility and deployment status.

## Execution Record

- Baseline: HEAD 010d5f1; 13 officials, eight institutions, 39 excerpts. Congress: 649 profiles, 15,637 stored statements, median 12. The existing federal pipeline uses four broad source groups and has 61 queued source pages.
- Parallel roster research is isolated in /private/tmp/federal_roster_{white_house,commerce_economy,security_agencies}.json. The coordinator owns integration and production changes.
- Existing API budget: OpenRouter lifetime cap $350; approximately $164.30 recorded. X and govinfo credentials are absent. No budget increase is authorized or needed for the first research run.

- Implemented 150 people and 36 institutions across 41 organizations and 15 daily source groups. All 186 profiles completed eight separate historical search passes. Separate requests ensure the provider actually searches each topic.
- Independent Astra review found four material issues: copied reporting context, incomplete source retries marked complete, query starvation, and an escaped download link. Fixed all four and added regression coverage. The full suite passed 78 Python tests and 20 JavaScript tests. No review findings remain deferred.
- Browser verification confirmed historical roles, per-person evidence counts, source gaps, and a functional coverage CSV download.

- A live low-evidence audit found two strict verifier gaps: dotted month abbreviations and prepared-for-delivery speech headers. Added failing regressions, fixed both, and recovered cached candidates without new search calls.
- Live timing justified four concurrent daily searches per group. A barrier-based regression proves overlap and coordinator-only writes. Shared client reservations still bound in-flight cost. The old sequential run stopped after saved checkpoints; the updated run resumes those checkpoints.

- The full `make site` check exposed an existing dependency on ignored congressional raw files. Moved the next-Congress calculation into the roster refresh. The site target now uses tracked inputs, and the clean-fixture regression and full build pass. Congressional roster, scores, daily labels, statement log and member export remain unchanged.

- Final attribution audit recovered explicit government memo and testimony headers. Independent review caught a recipient-as-author error before these rules ingested evidence. Fixed it by binding the name directly to the authorship marker through recognized titles only; removed generic prepared-for attribution. Negative tests cover recipients, other speakers, and name lists. The reviewer confirmed the fix. All existing document-author excerpts still satisfy the tightened header rules or the specific government transcript rules.
- Final suite after these code changes: 82 Python tests and 20 JavaScript tests pass. The lockfile check and whitespace check pass. The expanded live collection completed all 111 query checkpoints, checked 60 pages, added 83 excerpts, and retained 377 pages for later runs.
- Historical collection retained 1,522 excerpts from 687 source pages after all 1,488 search passes completed. The government-source pass checked 524 distinct pages and retains 18 pages for retry. Eleven people have no verified excerpts. The federal median remains five excerpts; the congressional median is twelve. The coverage audit records these gaps and missing archive channels.
- All 396 federal policy pairs have model assessments across 306 candidate statements. DeepSeek supplied 309 accepted final judgments. Astra supplied 78 accepted final judgments; nine cases still need human review. No federal model calls remain pending. All 2,486 pre-existing judgment records remain identical. Invalid output passed after smaller retries; budget reservations deferred three concurrent Astra requests, which completed with two workers.
- A fresh upstream fetch found the November 8 congressional update at f4c83e6. Integration preserves that update and every cost-ledger record before the final push.
- Resolved the shared ledger and generated member-export conflicts. The merged ledger retains all 7,617 records. All congressional evidence and core data match upstream exactly; Congress now has 15,728 excerpts. The merged tree passes all 102 tests, the full site build, lockfile validation, and whitespace checks against upstream. The browser shows 150 researched officials, zero pending federal judgments, and the remaining source queue without console errors.
