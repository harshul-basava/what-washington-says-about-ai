# Use the official X API for federal collection

The user requested the official X API and required verification of the existing secret before work continued. The original repository's November 8 run confirms a nonempty `X_BEARER_TOKEN` and 16 successful full-archive queries. The workflow ran commit `13d73ca4c79d63cfda8b04cbb163ac5553493927` and returned one new statement: https://github.com/harshul-basava/what-washington-says-about-ai/actions/runs/42501918942.

The current account has read-only access upstream. The fork and local environment lack that bearer token. The implementation will go to the existing PR branch for the original repository. Its owner must merge and run it there. Do not extract GitHub secrets, change permissions, run paid collection locally, or move the fork default branch to a configuration that lacks its required secret.

## Implementation

- Add an official full-archive transport with `X_BEARER_TOKEN`, account identity checks, complete post text, exclusive date bounds, and resumable pagination.
- Preserve the existing author, role-date, exact excerpt, quotation-length, deduplication, and stable statement-ID checks.
- Separate official API checkpoints and cached responses from emusks cursors. Carry forward pinned account identities, but never infer official API completion from an emusks run.
- Cap each invocation at an additional $2 by default. Share the existing X lifetime and monthly daily limits. Account for both post reads and user lookups. Reduce page size to fit the remaining allowance and stop safely before overspending.
- Use conservative request pacing, honor server cooldowns, redact errors, and retain pending work after authentication, budget, rate-limit, or partial-response failures.
- Select the official provider in the registry and original daily workflow. Keep emusks available only through an explicit provider selection. The site must identify the provider and show that official collection has not yet run.
- Test the transport with controlled HTTP responses and the coordinator with temporary repositories. Run both full suites and the offline build, obtain independent review, and update PR #2. Do not claim a live official federal run occurred.

## API references

- https://docs.x.com/x-api/posts/search-all-posts
- https://docs.x.com/x-api/users/get-user-by-username
- https://docs.x.com/x-api/fundamentals/rate-limits
- https://docs.x.com/x-api/getting-started/pricing

The documented search maximum is 500 posts per request. Full-archive requests have a one-per-second limit and a 300-per-15-minute limit. Post reads cost $0.005 and user reads cost $0.010. These prices inform conservative local estimates; the X console remains authoritative.

## Verification

The full suite passes: 129 Python tests and 28 JavaScript tests. The offline site build, historical plan, and whitespace checks pass. The plan reports 23 official historical intervals awaiting collection. Browser verification confirms the official-provider label, its not-started status, and the retained 1,114 X excerpts.

Independent review identified a cost durability gap after worker termination. The collector now records the maximum request reservation before HTTP and appends a correlated reconciliation after a response. Interrupted or unknown outcomes retain the reservation. The regression test reproduces the interruption and confirms that a new client respects the shared cap. Independent follow-up review reproduced the fixed behavior and found no remaining actionable issues.

All evidence, judgments, existing X checkpoints, congressional data, and cost-ledger records remain byte-identical to `4de4196`. The export revision matches its charts. Credential checks found no local secrets in publishable files. No paid calls ran during this switch. Live federal API acceptance and billing still require the first authorized run in the original repository after merge.

## Authorized merge and live collection

The user subsequently requested the merge and historical search. Their GitHub account then had write access upstream. PR #2 merged as `8557823` on November 8. A reviewed manual workflow now uses the original repository's secrets, shares the daily queue, and checks out the latest default branch after a queue wait. It preserves costs and evidence on failure. Its batch outcome accepts bounded page or cost limits while rejecting authentication, cooldown, source, and judgment errors.

The official historical cutoff moved to November 8, exclusive, because the previous November 9 cutoff was still in the future. A separate daily pass covers the current period. Four historical batches completed all 23 intervals across 47 successful pages, adding seven excerpts. The daily pass completed 18 active account windows across 22 pages and added no excerpts. All windows and model requests finished. Existing ten human-review pairs remain excluded from accepted charts.

Estimated added cost was $6.675 in X reads and less than one cent for one DeepSeek judgment. All earlier 18,794 excerpts, 4,384 assessments, emusks checkpoints, and congressional data remain unchanged. The original daily workflow is active. The fork's duplicate daily workflow is paused to avoid duplicate collection and charges. `data/federal_x_official_completion.json` records the five runs and aggregate checks.
