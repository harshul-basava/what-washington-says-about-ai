# Federal X historical collection and daily activation

The user authorized a live historical search, site updates, and daily updates. They explicitly authorized X_AUTH_TOKEN and OPENROUTER_API_KEY in their fork, kaustubhkislay/what-washington-says-about-ai. The upstream repository grants this account read-only access. Do not merge or change upstream settings.

Use the current branch and existing DeepSeek/Astra cascade. Keep the existing spending caps. Preserve source attribution, existing evidence IDs, and congressional data. Never print or commit either secret. Baseline: 5dbca60; OpenRouter spend $226.7468; no imported federal X posts.

The implementation decision is to paginate each account's full permitted historical interval, with a fixed end of 2026-11-09. This avoids 945 mostly sparse monthly queries. Retain monthly mode as an option. A new cursor after an empty page must continue; an empty page alone cannot establish completion. Keep the 20-second request interval and persisted cooldown. Daily collection retains its independent overlapping windows.

- [x] Save both authorized secrets in the user's fork.
- [x] Test and add account-wide historical intervals, frozen end dates, and coverage checks for changed interval modes.
- [ ] Run historical collection to completion or document specific source failures. Resume bounded invocations and preserve cooldowns.
- [ ] Assess new policy evidence, rebuild the site, and verify evidence integrity and visible coverage.
- [x] Configure the fork's schedule for federal-only updates, retaining explicit source overrides. Review and test changes.
- [ ] Push the PR branch and fast-forward the fork's default branch to activate the authorized daily workflow. Verify a workflow run. Leave upstream unmerged.

## Execution record

- GitHub CLI stored both secrets through stdin, without command arguments or logs containing their values.
- This request supersedes the earlier no-live-search instruction. The prior bounded smoke test returned 20 BIS posts; 18 passed evidence checks.

- Independent review found stale date-bound checkpoints and moving future cutoffs. Regression tests now cover both fixes. Account history requires a fixed exclusive cutoff at or before UTC tomorrow. The focused re-review found no remaining issue.

- Live pagination exposed an emusks 2.3.20 compatibility issue: X returned `TimelineTerminateTimeline` with direction `Bottom` while the library retained a cursor. The bridge now honors this explicit end marker. Empty pages without that marker still continue. A regression test failed before the fix and passed afterward; independent review found no issue. Temporary raw-instruction diagnostics were removed.
