# Policy judgments implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task by task.

**Goal:** Add evidence-backed judgments about named AI policies, export controls, embedded independent verification organizations, and China race dynamics to the pipeline and website.

**Architecture:** Keep the existing five scores intact. A versioned policy registry drives candidate retrieval and two independent model judgments. A deterministic exporter preserves disagreement, missing evidence, dates, and source quotes. A standalone browser component presents the results on the existing static site.

**Tech stack:** Python 3.12 standard library, existing llm.py gateway, static JavaScript, unittest and node:test.

**Spec:** The user approved code and website changes with per-policy stance, dates, source quotes, and model disagreement on 2026-11-07. This document records implementation choices.

## Global constraints

- Never infer a named bill position from general regulation or China sentiment.
- Support, oppose, mixed, neutral description, unclear, and not relevant are separate statement labels.
- No matching evidence, no relevant evidence, and incomplete assessment are separate coverage states.
- Generic independent audits do not establish support for embedded auditors.
- Preserve every judgment, quote, date, judge, and reason. Do not average opposing labels.
- Use registry IDs and dates for each new framework/version; refresh is manual, with no new automation.
- Use verified existing evidence; retain upstream verification limitations. No paid search is required.
- Run a 20-person pilot before a paid run projected above $5; use the existing gateway and project budget.
- Cache keys include evidence, registry definitions, rubric, and model; changed inputs require new judgments.

## Review focus

- A model skips a requested judgment: reject the response instead of calling it silence.
- Generic car kill switches or unrelated audit language: candidates require semantic rejection, never keyword scoring.
- Evidence changes or a policy version changes: invalidate prior judgments.
- Support and opposition coexist, or judges disagree: preserve both in the browser and export.
- Partial dates or missing dates: do not infer a latest position or a precise change date.

## Task 1: Registry, rubric, and deterministic evidence core

Files: config/policies.json, config/policy_rubric.md, policy_judgments.py, tests/test_policy_judgments.py.

Interfaces: candidates(root, registry) returns verified statement records with keys and candidate targets; validate_response(text, items, registry) validates complete labels; summarize(records, candidate_count) produces stance and coverage.

- [x] Write tests for omitted labels, invented sources, stale evidence, mixed positions, false bill matches, and no evidence versus pending review.
- [x] Run unittest and observe failures before implementation.
- [x] Implement registry validation, candidate retrieval, prompt construction, response validation, stable input hashing, aggregation, and export.
- [x] Run the tests until all pass.

## Task 2: Model runner and populated outputs

Files: scripts/phase3_policies.py, Makefile, data/policy_judgments.json, site/data/policies.json, site/data/policy_members/, site/data/policies.csv.

Interfaces: plan is read-only; label uses the gateway and writes resumable caches; build works offline from published judgments and evidence.

- [x] Add integration tests for offline exports and stale/partial results.
- [x] Add plan, label, and build commands, with per-run spending limits and progress reporting.
- [x] Run a 20-person pilot, inspect errors and examples, then complete both judges within the project budget.
- [x] Rebuild the policy exports from the published judgment file and verify counts and provenance.

## Task 3: Website, documentation, and final review

Files: site/policies.js, site/policies.css, site/index.html, tests/policies.test.cjs, README.md.

Interfaces: policies.json supplies registry and compact member summaries; per-member JSON supplies the full dated quote history and individual model reasons.

- [x] Test filter behavior, HTML escaping, missing states, and conflicting judgments.
- [x] Add policy, stance, party, and name filters, summaries, and expandable source quotes.
- [x] Document how to add and version frameworks, refresh judgments, and rebuild without raw research files.
- [x] Run all Python and JavaScript tests and inspect the browser on desktop and mobile.
- [x] Request one fresh code review; resolve material findings and rerun the relevant tests.

## Progress

- The local checkout uses branch codex/policy-judgments. The original repository remains unchanged remotely.
- The user approved implementation. Continue within that scope without another approval for routine reversible edits.

## Verification results — 2026-11-07

- The final corpus has 2,425 candidate statements from 411 people, with 2,844 statement-policy pairs across 10 targets. Both configured models returned a valid judgment for every pair. All 649 roster members have explicit coverage states.
- The 20-person pilot cost $0.426. All policy calls, including retries and the updated FRONTIER definition, cost $8.2525 across 326 requests. The ledger records the calls.
- The full run left 22 incomplete Claude batches. Smaller batches resolved all but one response. That response contained a valid fenced JSON result after prose. The parser now accepts one fenced result and still rejects missing pairs or multiple result blocks. The final saved response was recovered without another paid call; its generation ID and recovery flag remain in the judgment file.
- A fresh reviewer found a partial-date ordering issue, the missing FRONTIER bill-number alias, and missing detail data presented as absent evidence. All three have regression coverage and fixes.
- Seventeen Python tests and five JavaScript tests passed. Coverage includes cache invalidation, complete output validation, partial dates, budget reservations, filters, source escaping, and missing detail data.
- The offline build passed without OPENROUTER_API_KEY. The final plan reports zero uncached requests. Published summaries contain no pending or partial assessments.
- Browser checks covered policy and stance filters, name search, source expansion, both model reasons, the navigation link, and desktop/390px mobile layouts. The policy section has no horizontal overflow on mobile. No browser errors appeared.
- The site and data remain local on codex/policy-judgments. No remote push or deployment occurred.
