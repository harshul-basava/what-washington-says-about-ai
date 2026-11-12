# Federal archive collection implementation plan

**Goal:** Collect more current officials' AI statements from primary testimony and speech archives without repeated paid discovery or weaker verification.

**Architecture:** A bounded archive collector discovers links through official indexes and the repository's hearing/source inventory. It downloads each canonical document once per check interval, hashes normalized text, and extracts only AI-related chunks with eligible named officials. One extraction covers all selected officials in a chunk. Persisted source/chunk signatures and negative results prevent repeat model calls. The existing exact quote, attribution, date, eligibility and evidence-ID validators remain authoritative.

**Tech stack:** Existing Python/httpx/HTMLParser/pypdf, DeepSeek extraction, existing judgment pipelines and Astra review.

**Authorization:** User requested implementation and a pilot within the existing budget. Routine design choices below are implementation decisions. Existing internal review tool remains local and excluded from commits.

**Constraints:** Pilot cumulative OpenRouter ceiling $10, collection ceiling $2, no paid X collection, no cap changes. Check original repository credit before execution. Use the existing GitHub daily concurrency group. Store full source text only in ignored raw caches. Rejected attribution stays unresolved. No claim of exhaustive archive coverage.

## Tasks

- [ ] Add tests and collector: allowlisted archive links; bounded documents/chunks; unchanged and negative-cache reuse; source/prompt/subject changes invalidate extraction; malformed/rejected rows remain visible without repeat paid calls; partial cursors resume; cross-source excerpt overlap rejected; exact validators retained.
- [ ] Add CLI and fixed cumulative pilot runner. Retain baseline on retries; reserve review funds. Use current eligible people only. Archive config includes Fed speech/testimony indexes, Commerce speech index, and existing official hearing URLs. Preserve source-specific gaps.
- [ ] Add optional daily archive collection under existing collection allowance and manual pilot workflow. No extra schedule. Run ordinary analysis/policy judgments and targeted Astra review after pilot evidence collection. Save results and cache on failures.
- [ ] Run unit/full tests, independent review, zero-paid discovery preview, bounded live pilot, source spot checks and zero-new-request repeat. Build local site, report yield and costs, commit/push only collector and public evidence changes.

## Review focus

Budget resets across retries; changed/partial sources; cross-speaker attribution; duplicate mirrors/excerpt splitting; stale eligibility. Tests exercise each relevant path.

## Execution log

- Existing branch codex/policy-judgments reused; internal review changes left untouched.
- Prior original-repository credit: $22.721652 usable, before $0.635063 later spending. Fresh read-only check dispatched.
