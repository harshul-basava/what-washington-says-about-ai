# Federal Roster Expansion Implementation Plan

**Execution update, November 10, 2026:** The user reduced the active roster to **500 current federal people total**, including existing profiles. Institutions remain separate. Preserve other discovered roles in the inventory without active collection. The original eight-pass research and Astra method remains in use. The current authorized OpenRouter lifetime cap is $500, and the federal daily model allowance is $4; these upstream approvals supersede the older values below. No increase to $800 was approved. The pilot and daily scheduler are complete. See [the execution record](../../federal-roster-expansion-progress.md) for verified costs and remaining work.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cover influential current officials across all executive departments, White House offices, intelligence and cyber agencies, independent agencies, and their substantive offices.

**Architecture:** Extend the existing subject registry, current-service gate, research pipelines, and static federal site. Add a sourced role inventory to expose missing offices and people. Release verified additions in cohorts with separate research and daily-update status.

**Tech Stack:** Python 3.12+, uv, JSON configuration and audit files, existing OpenRouter and official X clients, static HTML/JavaScript, GitHub Actions, unittest, and Node tests.

**Spec:** [Federal leadership and office coverage](../specs/2026-11-10-federal-roster-expansion-design.md).

## Global Constraints

- Current government officials and government institutions only; exclude former officials, private commentators, informal advisers, and contractors.
- Senior leadership qualifies without AI evidence. Other officials need sourced decision authority. A missing score or X handle never excludes an eligible person.
- Cover all departments, White House offices, CIA, NSA, CISA, intelligence components, independent agencies, and substantive component offices.
- Preserve one subject ID per person, separate official/institution counts, evidence attribution, original statement IDs, and observed histories.
- Reuse the congressional five questions and 23 categories. Keep all current models, rubrics, and confidence thresholds.
- Keep lifetime caps at OpenRouter $350, X $150, Exa $100; monthly daily caps at $35, $40, $10 respectively.
- Keep X batches at $2 and the federal daily judgment allowance at $2. Pilot aggregate limits: OpenRouter $12, X $4, metered search $2.
- Use the existing original-repository secrets. Do not export secrets, add a second daily scheduler, or change budget limits automatically.
- The requested deliverable is this plan. Its tasks remain unexecuted.

## Review Focus

- A current official with no AI remarks remains visible, with no invented stance. Test in Tasks 2 and 6.
- An office reorganization or failed directory request preserves identity and creates a review issue. Test in Tasks 1 and 5.
- A person with multiple appointments counts once and appears in each relevant office filter. Test in Tasks 2 and 6.
- A reused X handle never attributes another owner's posts to the official. Test cohort cutoffs and ownership in Task 3.
- Budget exhaustion leaves explicit pending work and does not starve a newly added agency. Test in Tasks 4 and 5.

## Baseline and order

The local checkout on 2026-11-10 contains 62 eligible officials and 35 institutions. The broader registry has 186 profiles, including 89 excluded profiles. Recompute this baseline before execution; do not reactivate excluded people to reach a number.

First inventory all agencies and offices. Then prioritize White House, Commerce, CIA, NSA, CISA, intelligence leadership, and superintelligence bodies. Next fill every other department and independent agency. Review existing officials alongside new candidates.

The first deliverable is a table of covered and missing offices with proposed incumbents. Determine the total roster from that table. No arbitrary headcount limits the search.

## File responsibilities

| Files | Responsibility |
|---|---|
| New `config/federal_roster_inventory.json` | Agency discovery, role coverage, sources, and disposition of candidates. |
| New `federal_roster.py`; new `tests/test_federal_roster.py` | Offline inventory validation and public coverage report; no eligibility mutation. |
| `config/policy_subjects.json`; `config/federal_scope.json`; `evidence/<id>.json` | Canonical subjects, organizations, current-service decisions, and verified statements. |
| New `data/federal_roster_expansion.json` | Frozen cohort IDs, archive cutoff, spending baseline, and per-profile completion stages. |
| New `data/federal_roster_expansion_review.json` | Separate Astra review of the new cohort. |
| Existing research, X, analysis, daily, and build modules | Collect and analyze new subjects through existing interfaces. |
| `federal_coverage.py`; `site/federal-analysis.js`; `site/federal-charts.js`; `site/federal.html` | Publish coverage, office filters, roles, and existing charts. |
| New `docs/federal-roster-expansion.md`; existing scope/coverage reports | Publish sources, results, unresolved gaps, and costs. |

### Task 1: Create the office inventory and validate its coverage

**Files:** Create the inventory, `federal_roster.py`, `tests/test_federal_roster.py`, and `docs/federal-roster-expansion.md`. Read the registry and scope files without changing eligibility.

**Interfaces:** `load_inventory(root: Path) -> dict` validates the schema described in the spec. `coverage_report(root: Path) -> dict` returns organization and role counts, distinct included people, unresolved roles, and discovery gaps. `uv run --no-dev python federal_roster.py report` prints this report without network calls or writes. Invalid input exits nonzero.

- [ ] Inventory all 15 departments, all Executive Office units, the intelligence-community directory, and all executive/independent agencies in the federal directory. Follow component directories recursively; record visited pages and unresolved links.
- [ ] For every organization, review leadership and substantive offices using the two inclusion rules in the spec. Record current incumbents, vacant roles, nonpublic incumbents, and out-of-scope results with sources. Include all qualifying leaders, whether or not they discuss AI.
- [x] Write tests asserting that an `included` role without eligible person scope fails validation, one person in two roles counts once, and a pending component prevents an organization-complete claim. Assert that a page-fetch error cannot produce a `vacant` state and that a renamed organization retains its stable key.
- [ ] Run `uv run --no-dev python -m unittest discover -s tests -p 'test_federal_roster.py' -v`; confirm the new behavior fails before implementation.
- [x] Implement the validator and report. Require unique role IDs, valid source URLs/check dates, resolved parent links, and explicit review reasons. Do not infer that a directory contains every influential person.
- [ ] Run the focused tests and `uv run --no-dev python federal_roster.py report`. Publish counts by agency, seniority, existing/new person, and unresolved reason. Mark incomplete discovery clearly.
- [ ] Commit the inventory, validator, tests, and sourced gap report together.

### Task 2: Add verified current officials and define cohorts

**Files:** Modify `config/policy_subjects.json`, `config/federal_scope.json`, `config/policy_source_manifest.json`, and `docs/current-federal-scope.md`. Create empty evidence files and `data/federal_roster_expansion.json`. Extend `tests/test_policy_subjects.py`.

**Interfaces:** Keep `policy_subjects.load_subjects(root)` as the sole active-roster gate. The expansion manifest stores `version`, `created_on`, baseline revision/counts, `cohorts`, and `profiles`. Each cohort stores its subject IDs, UTC archive interval, spending baseline and limits. Each profile records role IDs plus web, X, analysis, Astra, and daily-routing status.

- [ ] Verify current service immediately before adding each person. Prefer current official directories; independently corroborate ambiguous advisory roles and stale appointment announcements. Preserve the source's exact current title and historical aliases.
- [ ] Write regression cases for an eligible official with zero excerpts, an acting official, an outside adviser, and one official with a second role. Assert that only eligible people reach both collectors and public exports, and that a second role preserves evidence/history under one ID.
- [ ] Run `uv run --no-dev python -m unittest discover -s tests -p 'test_policy_subjects.py' -v`; confirm any new behavior fails before changing shared validation.
- [x] Add verified officials, organizations, parent relationships, role sources, and explicit empty evidence files. Record unresolved people in the inventory only. Recheck existing uncertain advisers under the same rule.
- [x] Freeze five pilot IDs: one White House official, one Commerce official, one intelligence/cyber official, one official from a missing department, and one independent-agency official. If a category has no verified addition, record the reason and select another undercovered category.
- [x] Assign remaining verified additions to cohorts of 10–20. Include empty profiles in the roster; do not treat cohort membership as completed research. Store current inventory counts and updated ledger baselines.
- [ ] Run eligibility tests and the inventory report. Commit each coherent agency cohort with its scope evidence.

### Task 3: Run bounded historical web and X research

**Files:** Modify `config/federal_research_seeds.json`, `config/federal_x.json`, `scripts/federal_x.py`, `scripts/federal_x_api.py`, `federal_x_config.py`, and `.github/workflows/federal-x.yml` where needed. Update evidence and research audit files. Extend `tests/test_federal_research.py`, `tests/test_federal_x.py`, and `tests/test_federal_x_api.py`.

**Interfaces:** Reuse `scripts/federal_research.py ... --ids`. Add optional `--until YYYY-MM-DD` to X `plan` and `collect`: an exclusive UTC archive bound, historical mode only. It overrides the cutoff only for selected IDs. Add `subject_ids` and `historical_until` workflow inputs with validation and safe environment-variable quoting. Defaults preserve current behavior. Do not reset existing archive progress.

- [x] Write tests for cohort-specific cutoffs, pagination resume, unchanged existing jobs, moved account ownership, and mismatched numeric authors. Assert that daily mode rejects a historical-only cutoff. Run the focused X tests and confirm failures for the new interface.
- [x] Implement the cutoff through planning, request parameters, persisted job identity, status, and coverage reporting. Keep unrelated jobs valid. Implement workflow subject filtering without interpolating untrusted input into shell code.
- [x] Source account mappings from government links or corroborated account identity. Preserve ownership dates and numeric author checks. Record `no_verified_account` separately from `not_searched`.
- [x] Run offline plans for the pilot:

```bash
uv run --no-dev python scripts/federal_research.py plan --ids "$COHORT_IDS" --rounds 8
uv run --no-dev python scripts/federal_x.py plan --mode historical --ids "$COHORT_IDS" --until "$COHORT_UNTIL"
```

- [x] Refresh shared ledgers and confirm remaining pilot allowance. Run eight web passes and targeted official sources with `research` and `seeds`; set each command's `--max-cost` to the remaining aggregate allowance, rather than granting a fresh pilot allowance each time.
- [ ] Dispatch bounded X collection on the original repository using its existing secret. Preserve the shared `daily-update` concurrency group. Pull completed evidence/cost changes before another local paid run. Historical posts start at 2023-01-01, clipped to account ownership; relevant older sources may enter through web research.
- [ ] Resolve verification failures and retrieve full speeches/transcripts for promising leads. Record contrary evidence, source access gaps, archive limits, and zero-result searches. Preserve stable statement IDs and explicit personal/official/institutional attribution.
- [x] Run focused tests and publish the pilot's evidence, search coverage, elapsed time, and actual costs. Forecast remaining work before expanding. Commit progress, including incomplete stages, without calling a bounded batch a complete search.

### Task 4: Complete shared analysis and Astra review

**Files:** Reuse `scripts/federal_analysis.py`, `federal_analysis.py`, `federal_analysis_models.py`, and `federal_stance_review.py`. Modify `scripts/phase3_policies.py`, `.github/workflows/federal-x.yml`, and `.github/workflows/federal-stance-context.yml`. Create the separate expansion review audit. Extend `tests/test_policy_runner.py`, `tests/test_federal_analysis.py`, and `tests/test_federal_stance_review.py`.

**Interfaces:** Add optional `--ids` to named-policy `plan` and `label` to filter subject IDs before candidate selection. Keep `--targets` reserved for policy IDs. Unknown IDs fail clearly. Forward the X workflow's subject selection to both analysis stages. The existing `federal_stance_review.py --audit` interface consumes a frozen manifest in `data/`; never overwrite the earlier 33-case or 32-case audits. Add an optional `audit_path` input to the context workflow, restricted to existing JSON files directly in `data/`, with the existing audit as its default.

- [x] Test policy subject filtering, zero-evidence profiles, incomplete model responses, and exhaustion of a shared model allowance. Assert that pending work never becomes a silence score or accepted stance.
- [x] Implement the subject filter and rerun focused tests. Keep the five-score, regulation, summary, topic, and named-policy prompts unchanged.
- [ ] Run offline broad-analysis and named-policy plans for each cohort. Run resumable labels within the remaining aggregate model allowance; use `--budget-baseline` where supported and remaining allowance elsewhere.
- [ ] Complete base analysis before the final review. Create the expansion audit explicitly with only new evidence-bearing IDs; do not let its default missing-file behavior select all existing no-stance profiles.
- [ ] Run Astra `review` against the separate audit. Retrieve any requested web or X context, then review again as needed. Pass the expansion audit to the original-repository context workflow for secret-dependent X calls. Import returned context and cost artifacts before the next paid call. Apply only valid, current-input results; preserve unresolved and no-stance decisions.
- [ ] Test that changed evidence invalidates a review, repeated apply is idempotent, no-evidence profiles need no model calls, and prior observed snapshots remain unchanged.
- [ ] Report all five scores, 23 categories, cited summaries, topics, histories, named-policy status, and final Astra status separately. Commit analysis and audit artifacts with the cohort evidence.

### Task 5: Add daily collection and role freshness checks

**Files:** Modify `config/federal_sources.json`, `scripts/daily/federal.py`, `scripts/daily/federal_sources.py`, `federal_coverage.py`, and `.github/workflows/daily.yml` only where needed. Extend `tests/test_federal_daily.py` and `tests/test_federal_roster.py`. Store role-review observations in `data/federal_role_checks.json`.

**Interfaces:** Every eligible profile receives a named query and organization-source assignment. Extend `coverage_report(root)` with last role check and pending role-review counts. A weekly check inside the existing daily workflow retrieves known directory URLs and records `unchanged`, `review_needed`, or `unavailable`. It never edits scope decisions automatically. Use content hashes of relevant directory text; preserve the last successful check on failure.

- [ ] Test a new department, a linked office, a new verified account, and a newly eligible person with no evidence. Assert that each receives the required daily assignment exactly once.
- [x] Test repeated small budgets with a fake client: oldest pending collection and judgment work must advance across agencies and analysis stages. Extend scheduling only if the current logic starves a group or stage.
- [ ] Add source domains, queries, institutional sources, and verified active X mappings. Add last-success, pending-stage, and oldest-pending metrics without changing spending caps.
- [x] Test directory content changes, temporary 403 responses, and role renames. Confirm these create review records without automatic exclusion or duplicate people.
- [x] Implement the weekly check in the existing workflow with a timeout and cached source records. Include the new review file in normal progress commits. Keep the fork's duplicate schedule paused.
- [ ] Run `uv run --no-dev python scripts/daily/run.py --sources federal --dry-run`. Confirm every cohort ID has routing. Then observe one authorized bounded live run and report completed work, backlog age, and estimated full rotation time.
- [ ] If capacity cannot support daily collection for every profile, retain the explicit queue and report the limit. Request a concrete budget or frequency decision only after measuring it. Commit routing, tests, and coverage reports.

### Task 6: Publish office coverage with the existing charts

**Files:** Modify `federal_coverage.py`, `scripts/phase5_build_site.py`, `site/federal.html`, `site/federal-analysis.js`, and `site/federal-charts.js`. Extend `tests/federal-analysis.test.cjs`, `tests/federal-charts.test.cjs`, and relevant Python export tests. Update scope and expansion reports.

**Interfaces:** Add an additive `roster_coverage` object to the existing federal export, from `coverage_report(root)`. It lists organization discovery status, unique included people, role states, and last verification. Keep existing score/history fields and matching export revisions. Expose only role facts and source links, not internal candidate speculation.

- [x] Test department totals, office filters, dual appointments, empty profiles, and people/institution separation. Assert that all eligible people contribute to coverage bars, including unscored people.
- [x] Test that unresolved candidates never become profiles and that missing inventory data produces an unavailable coverage notice rather than a false zero.
- [x] Add office navigation, sourced role details, and an agency coverage table. Distinguish roster gaps, research gaps, no stance, and pending analysis. Keep Congress-style visuals and the same question labels.
- [x] Build with `make site PY='uv run --no-dev python'`. Verify congressional evidence, scores, histories, and substantive exports remain unchanged. Prevent a federal-only build from advancing a congressional update date without new congressional data.
- [ ] Run `make test PY='uv run --no-dev python'` and `git diff --check`. Inspect desktop and narrow-screen views for each major agency category, one multiple-role official, one no-evidence official, and an Astra-reviewed profile.
- [ ] Commit and publish each verified cohort through the existing GitHub and deployment path. Verify deployed roster counts, source links, office filters, and daily workflow status against the committed revision.

## Completion report

For every agency, report discovered/reviewed offices, included unique officials, unresolved roles, vacancies, historical-search completion, verified X coverage, judgment completion, and daily freshness. List sources and dates. Keep no-stance results visible.

The expansion is complete only when every discovered organization and qualifying role has a documented disposition, and all promised research/judgment stages finish or carry explicit unresolved limitations. A cost cap or inaccessible source is a reported limit, not a completed search. Continue beyond initial cohorts until the defined scope is covered.

## Planning check

This plan keeps roster discovery separate from research and scoring. The interfaces use existing commands except the explicitly proposed subject filter, historical cutoff, and inventory report. Implementation must refresh current titles, organization structure, pricing, and ledger totals before paid execution. No final headcount or completion date is promised before the inventory and pilot.

The independent design check found no consequential unanswered questions. The author checked the plan against the design and corrected the workflow inputs needed for cohort-specific judgments and Astra context retrieval.
