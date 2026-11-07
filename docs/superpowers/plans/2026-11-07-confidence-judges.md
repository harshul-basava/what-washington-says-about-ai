# Confidence-based policy judgments

The user chose DeepSeek V4.1 Flash 1017 after approving a first judge with confidence and Astra escalation. The initial configurable threshold is 0.80. This changes the policy pipeline only; the original five scores keep their existing method.

- Primary: deepseek/deepseek-v4.1-flash-1017. Reviewer: openai/gpt-6-astra.
- Every statement-policy pair gets a numeric self-reported confidence for the entire classification, including relevance and additional labels. Scores are not calibrated accuracy estimates.
- Primary confidence below the threshold requires an independent Astra judgment. Astra sees only evidence and rubric. Its final label takes precedence, while both original judgments remain visible.
- Astra confidence below the same threshold requires human review. Such records cannot become accepted positions or absence of evidence.
- Keep previous dual-judge results in their existing file. Save new results separately, with per-pair input hashes, model IDs, dates, and generation IDs. Configuration changes must not silently reuse incompatible results.
- Resume primary and review stages with one shared per-invocation cost limit. Use live model metadata, supported parameters, and prices. Run a small pilot before the complete refresh.
- Update quote details, coverage text, charts, downloads, README, and exact prompt catalog to describe the new method accurately.
- Resolve the AI Action Plan qualified-support contradiction without changing the other policy questions.

Verification: threshold boundary and invalid scores; pending review and uncertain exclusions; reviewer-only routing; independent review prompts; stale-cache rejection; cost limit shared across both stages; offline exports and chart counts; quote rendering and browser checks.


## Validation and repository status

On 2026-11-07, all 32 Python tests and 13 JavaScript tests passed. The live pilot completed 165 statement-policy pairs: DeepSeek accepted 116 directly, Astra accepted 44, and 5 required human review. Browser checks verified both confidence scores, accepted Astra decisions, and human-review cases. The 390-pixel mobile viewport had no horizontal overflow, and the page reported no console errors.

The local feature branch is `codex/policy-judgments`, based on `9c0e1db`. A fresh fetch found GitHub `master` at `94787b1`, twenty commits ahead. Those commits add a separate daily workflow for the original five scores: unpinned DeepSeek V4.1 Flash runs three times, scores confidence from 1 to 5, escalates to GPT-6.1 Sol below 3.0 or on other triggers, and uses Astra for large disagreements. They do not contain this policy-specific feature or its pinned 1017 model and direct Astra threshold of 0.80. The local changes remain uncommitted; no push or deployment occurred.

The full local run and targeted retries completed all 2,844 statement-policy pairs from 2,425 statements across 411 people. DeepSeek accepted 2,167 pairs directly. Astra reviewed all 677 pairs below 0.80, accepted 594, and left 83 requiring human review. The offline plan reports zero pending model requests. The 83 unresolved pairs cover China dynamics (69), export controls (9), the AI Action Plan (3), embedded auditors (1), and the National AI Legislative Framework (1).

All confidence-pipeline calls, including the pilot and failed responses, cost $8.1451. The combined local and fetched upstream OpenRouter ledger totals $163.8843, below the $200 project cap. The main run cost $7.062; single-statement retries resolved the 14 failed DeepSeek batches. Astra returned valid responses for every requested review.

Final checks confirmed that summary, source-quote, and chart exports agree; every accepted judgment meets the threshold; every below-threshold DeepSeek judgment has an Astra assessment; and no unresolved case supplies accepted chart labels. All 45 tests passed again. A fresh browser reload verified the completed exports, final confidence details, chart coverage, and no console errors. The changes remain local and uncommitted. Upstream integration, publication, human review of the 83 cases, and empirical confidence calibration remain separate follow-up work.
