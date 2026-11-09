# Federal X Account Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Research all 165 unmapped federal profiles, add defensible account mappings, collect their public AI-policy history, and include them in daily updates.

**Architecture:** Three independent research groups inspect 55 profiles each. A shared audit records positive and unresolved findings. The coordinator validates the accepted mappings against the subject registry, retains exact attribution and ownership intervals, and uses the existing official X collector and original repository workflows.

**Tech Stack:** Python with uv, JSON registries and audit files, Exa search and source retrieval, official X API, GitHub Actions, existing static site exports.

**Spec:** User request in this chat: find verified X accounts for the remaining 165 federal profiles, run historical searches, and include them in daily updates.

## Global Constraints

- Preserve existing statement IDs, evidence, judgments, account pins, and completed checkpoints.
- Ownership needs an explicit official, personal-site, university, or credible independent source. A matching name, checkmark, self-description, or generic agency footer is insufficient.
- Keep institutions separate from people and child offices separate from parent agencies. Shared office handles need sourced ownership dates.
- Record a research outcome for every profile. Missing evidence remains unresolved; it does not establish that an account does not exist.
- Keep X credentials in the original repository's GitHub secret. Make paid collection and judgments through the existing capped workflows.
- Retain the current lifetime caps: X $150, OpenRouter $350, Exa $100. The user approved a daily monthly X cap of $40 on 2026-11-09 UTC. OpenRouter $35 and Exa $10 monthly caps remain unchanged. The X batch cap remains $2.
- Baseline: commit `fa9b1ec2bdc118ee6aa817f99be8bb5b9205ce7f`, 23 accounts for 21 profiles, 1,121 X excerpts. All original historical and daily X windows are complete.

## Review Focus

- Similar names, parody accounts, and agency share links must not become person mappings.
- Account renames and reused office handles must not attribute a predecessor's posts to a successor.
- An old identity source is not evidence of current availability; live API checks can reject or defer an account.
- Expanded daily coverage must fit the request and spending limits or clearly disclose pending work.
- Newly mapped accounts need fresh jobs, while unchanged accounts retain their completed history.

## Task 1: Source all remaining profiles

- [x] Search each of the 165 profiles and inspect ownership evidence.
- [x] Record accepted and unresolved accounts, source URLs, proof, queries, and research effort in `data/federal_x_account_research.json`.
- [x] Independently review accepted mappings and date bounds; resolve conflicting accounts before collection.

## Task 2: Integrate mappings and daily coverage

- [x] Extend `config/federal_x.json` with verified mappings only.
- [x] Confirm the unchanged collector generates historical and daily jobs for new mappings without discarding old checkpoints.
- [x] Evaluate daily workload and costs after the roster is concrete. Address observed capacity limits within authorized caps.
- [x] Update `docs/federal-x-coverage.md` and relevant coverage documentation. Rebuild the site and run the relevant tests.
- [ ] Obtain independent review and push the verified configuration to the original repository.

## Task 3: Collect, assess, and publish

- [ ] Dispatch bounded historical batches in the original repository and resume from checkpoints.
- [ ] Resolve concrete source or account errors; preserve unavailable outcomes in the audit.
- [ ] Run the current-period pass and policy judgments for accepted new evidence.
- [ ] Audit old evidence and assessment preservation, costs, coverage, and pending work.
- [ ] Publish the final audit and verify the deployed site and daily workflow state.
