# Executive and institutional coverage implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. The user authorized implementation of the discussed design.

**Goal:** Add source-backed executive officials and institutions to the policy explorer, including NSA, Commerce, and the White House Superintelligence Task Force.

**Architecture:** Keep the congressional roster and five-score pipeline intact. Merge an additional registry into policy publication only. Store dated roles separately from statement attribution; never propagate institutional positions to members. Give Congress, executive officials, and institutions separate chart denominators.

**Tech Stack:** Python 3.12, uv, static HTML/CSS/JavaScript, unittest and Node test runner.

**Spec:** The accepted scope is recorded below.

## Accepted scope and global constraints

- Add people and institution profiles, sources, dated roles, organization filters, and charts to the existing site.
- Preserve one identity per person. Membership can connect a person to several organizations; chart grouping uses one primary organization.
- Attribute each new quote as personal, official-role, or institutional. Preserve joint authorship without assigning each member a personal stance.
- Use the existing DeepSeek V4.1 Flash 1017 → independent Astra cascade below 0.80. Do not relabel unchanged congressional evidence.
- Verify membership and quotes from public sources. Show unknown dates and absent evidence explicitly. The initial registry is curated coverage, not a complete federal census.
- Preserve offline builds and the congressional daily pipeline. Document the manual source refresh path.

## Review focus

- An official with multiple roles must count once, including when filtered to the task force.
- An institution's statement must not become each official's personal statement.
- Unknown dates and roles must not create false chronology or confidence.
- Changes in attribution must invalidate its cached judgment; unchanged congressional inputs must retain their hashes.
- Empty agencies and small mobile views must remain usable and must not call officials independents.

### Task 1: Subjects, attribution, and offline publication

**Files:** Create `policy_subjects.py`, `config/policy_subjects.json`, `tests/test_policy_subjects.py`; modify `policy_judgments.py`.

**Interfaces:** `load_subjects(root)` returns the merged unique registry; `load_evidence(root, subject)` returns validated statements. Existing candidate keys and `members` exports remain compatible. New metadata includes `entity_type`, `branch`, `organization_id`, `organization_name`, `roles`, and `attribution` on statements.

- [x] Write and run failing tests for merged identities, invalid role references, attribution in prompts and hashes, offline exports, and unchanged legacy candidates.
- [x] Implement registry loading, statement validation, source-library export, conditional attribution prompt instructions, and metadata-sensitive export revisions.
- [x] Run the Python suite.

### Task 2: Explorer views and charts

**Files:** Modify `site/policies.js`, `site/policy-charts.js`, their CSS, `site/index.html`, and the two JavaScript test files.

**Interfaces:** Filters consume Task 1 subject metadata. Congress remains the default. Executive and institution scopes use organization grouping; membership filters include linked roles but each profile counts once.

- [x] Write and run failing tests for scope filters, multiple memberships, no-party subjects, attribution rendering, and organization chart grouping.
- [x] Add scope and organization controls, profile roles and source links, source-library access for profiles without policy matches, and organization chart groups.
- [x] Run both test suites.

### Task 3: Verified coverage and delivery

**Files:** Add curated executive evidence and source manifest; update README and current-prompt documentation.

- [x] Verify real public sources and role references; seed officials and institutions, including task-force leadership.
- [x] Validate exact source excerpts and record retrieval dates and hashes. Classify new candidates through the existing runner with a bounded budget.
- [x] Build exports, run all tests, inspect the dev site on desktop and mobile, and review the final diff.
- [ ] Commit and push to the existing fork branch under the user's prior push authorization. Check the PR for conflicts and report deployment limitations accurately.

## Execution record

- Pre-flight: Task 2 consumes the subject metadata and source library exported by Task 1. Task 3 supplies the same validated registry and evidence shapes.
- Ruling: Use the current feature checkout and execute locally. The user already authorized implementation and previously authorized pushing this branch.

- Tasks 1 and 2 complete: regression tests failed before implementation and now pass. The full suite passes 40 Python tests and 18 JavaScript tests.
- Task 3: 13 officials, eight institutions, 27 verified excerpts, and 32 additional statement-policy pairs. DeepSeek accepted 26 directly; Astra accepted five. One pair needs human review. No model requests remain pending.
- Final review: independent Astra reviewer found no critical, important, or minor issues. The reviewer confirmed that all 2,460 congressional candidate inputs and fingerprints remain unchanged.
- Browser verification: scope filters, Commerce and NSA subagencies, task-force role links, source expansion, both themes, and 320/390-pixel layouts pass without horizontal overflow or console errors.
- Source verification: exact normalized excerpts checked against retrieved pages; model classifications retain both assessments and uncertainty. Federal discovery and role updates remain manual.
- Upstream compatibility: merged `13d73ca` without conflicts. The shared website build and all 58 tests pass after the merge. The only legacy export change is its build date; all 649 member records remain identical.
