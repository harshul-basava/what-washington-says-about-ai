# What Washington Says About AI

This project tracks public statements about AI from Congress, executive officials, and federal institutions. The congressional roster also covers new members elected in 2026.

The congressional and federal views score public statements from 0 to 4 on five questions. Federal officials and institutions have separate views:

- **AI overall:** Will AI be good for Americans?
- **AGI:** Will AI reach human-level intelligence?
- **X-risk:** Can advanced AI cause a catastrophe, and does this need policy action?
- **China race:** Must the U.S. win the AI race with China?
- **Regulation:** Must the federal government make more rules for AI?

## How it works

1. **Collect.** We get AI statements from three sources:
   - posts on X, from the X full-archive search;
   - floor speeches and hearings, from the [CeSIA](https://cesia.org/en/data/attention/) dataset (CC BY 4.0);
   - press releases and news, from a web search.
2. **Verify.** We keep a quote only if it matches the text of its source page.
3. **Label.** The original congressional analysis uses two AI models (Claude Sonnet 5.5 and GPT-6.1 Sol). Each model gives a level for each question that the statement addresses. New congressional statements and federal statements use three DeepSeek passes, with independent Sol and Astra review when required. The rules for each level are in [`config/rubric.md`](config/rubric.md).
4. **Score.** A fixed formula changes the labels into a score for each person. The published score is the average of the scores from the two models.
5. **Review.** A person checks the scores where the two models do not agree.
6. **Policies they support.** A second rubric ([`config/reg_focus.md`](config/reg_focus.md)) lists 23 concrete AI policies (for example a data center moratorium or required reporting of AI layoffs). Two models (DeepSeek V4.1 Flash and GPT-6.1 Sol) mark each member's support or opposition for each kind, with quotes. GPT-6 Astra decides when they disagree. Output: `data/reg_focus.json` (`scripts/phase6_reg_focus.py`).

## Files

| Path | Contents |
|---|---|
| `config/` | Rubric and prompts |
| `scripts/` | Pipeline steps, `phase1` to `phase5` |
| `evidence/` | Verified statements for each person |
| `data/scores.json` | Scores, labels and reasons |
| `site/` | Static website |
| `analysis/` | Notebook and draft findings |
| `docs/` | Plan and assumptions |

## Run it

```bash
uv sync
cp .env.example .env   # add your API keys
make refresh           # collect, label, score and build the site
make serve             # open the site at http://127.0.0.1:8765
```

All paid calls go through `llm.py`. It stops at the budget limits in `budgets.yaml`.

## Policy judgments

The website also shows positions on specific policies. These judgments use a separate rubric from the five scores above.

- Named bills: the FRONTIER Act, the AI Kill Switch Act, and the Stop Stealing Our Chips Act.
- Frameworks: the 2025 AI Action Plan, the 2026 National AI Legislative Framework, the Great American AI Act discussion draft, and the White House AI Accord.
- Policy questions: AI export controls, embedded independent verification organizations (IVOs), and competition with China.

Each candidate quote receives a judgment from DeepSeek V4.1 Flash 1017 (`deepseek/deepseek-v4.1-flash-1017`). It returns a stance, additional labels, an evidence-based reason, a confidence score from 0 to 1, and a confidence reason. The score describes the model's confidence in the whole classification, including relevance and additional labels. It does not measure endorsement strength or calibrated accuracy.

A score strictly below the threshold in `config/policy_judging.json` (initially 0.80) triggers independent GPT-6 Astra review (`openai/gpt-6-astra`). Astra sees the original evidence and rubric, without DeepSeek's answer or score. Astra supplies the final classification if its confidence meets the threshold. Otherwise, the record requires human review and stays out of accepted stance charts. An uncertain `not_relevant` judgment follows the same review path. Exactly 0.80 meets the threshold.

The website preserves both assessments when Astra reviews a quote. It shows confidence scores, reasons, the review trigger, and the final judge. Model disagreement remains visible even when Astra resolves it. Human-review cases remain visible and cannot become "no relevant evidence." The previous Claude and GPT judgments remain in `data/policy_judgments.json`; the new pipeline saves separate results in `data/policy_cascade.json`.

The labels are support, oppose, mixed, description only, unclear, and not relevant. Additional labels describe export enforcement, auditor access, and competition tradeoffs. General support for audits does not establish support for embedded auditors. General regulation views do not establish a position on a named bill. The member summary covers the available accepted history and does not infer a current position. Both support and opposition produce a mixed summary. Missing assessments and human-review cases produce incomplete coverage.

Dates keep their original precision. A year-only quote can make the latest date year-only even when another quote has an exact date. An undated relevant quote prevents a latest-date claim. The quote list places undated quotes first, then sorts dated quotes by the end of their possible period. Partial dates appear first within a period. This order does not imply an exact sequence of events.

Coverage has separate states: no matching evidence, no relevant evidence after assessment, pending assessment, partial assessment, and complete assessment. None means opposition. Keyword retrieval can miss relevant statements. The judgments use the repository's existing verified corpus and inherit its source and attribution limits. They have not received a human validation study.

### Policy charts

The explorer has separate Congress, Executive officials, and Institutions views. Federal coverage contains 62 current officials and 35 active government institutions. The [current scope audit](docs/current-federal-scope.md) records sourced decisions for all 186 researched profiles. Former officials, private advisers, and unverified current roles remain outside the active roster. The roster covers the White House, Commerce, intelligence, defense, Treasury, State and trade, Justice, homeland security, energy, procurement, regulators, health, social security, and the White House Super Intelligence Force. The Justice Department task forces have separate profiles. This is a curated policy roster, not a complete federal census.

An agency filter includes its subagencies and linked roles. Each person counts once, even with several appointments. Executive and institution charts group profiles by their primary organization. Congressional charts retain party grouping. The views never combine people and institutions in one denominator. Profile links connect officials and institutions. Source statements remain available even when none matches the selected policy.

The additional registry lives in `config/policy_subjects.json`. `config/federal_scope.json` controls current eligibility for collection, judgments, and public exports. New or unreviewed profiles stay excluded until a sourced current-role decision exists. It records institution relationships, dated roles, aliases, and membership sources. Unknown start and end dates remain unknown. A role source can describe a historical appointment; its check date does not establish current service. Task-force membership includes clearly marked reporting sources. The White House Super Intelligence Force is separate from the Justice Department's task force. Historical sources may use CAISI/AISI or AISC; the current institutional pages use CAISSI and SISC.

Every new statement records attribution as `personal`, `official_role`, or `institutional`. Named officials' statements belong to their profiles. Institutional and joint statements do not propagate to members. The model receives attribution and role context. Changes to attribution invalidate that statement's judgment. The unchanged congressional candidates retain their existing cache hashes.

To extend federal coverage, edit the registry and add verified, stable `s1`, `s2`, etc. statements to `evidence/<subject-id>.json`. Match each excerpt against the source text, record its retrieval method, date, and text hash, and update `config/policy_source_manifest.json`. This collection uses exact matching after whitespace normalization. Where direct retrieval failed, verification used the search service's retrieved page text. This checks quote presence, not the source's factual claims or transcript accuracy. Do not reassign existing statement IDs or copy one collective statement into each member's file. Run `make policies-plan`, `make policies-label POLICY_ARGS="--max-cost 2"`, then `make policies-build`. A registry-only profile needs an explicit empty evidence file.

The daily job now searches federal sources and assesses new federal policy evidence. It covers the 97 eligible profiles in 15 source groups, through 67 agency and named search queries. Each eligible profile receives a named search assignment. The federal analysis page also provides five scores, 23 regulation categories, cited summaries, topics, and histories. Role and membership changes need manual review.

The initial federal search was a focused manual seed. Its 27 excerpts came from 16 distinct URLs. The source manifest lists 21 pages, including sources for roles. Sixteen excerpts used direct page retrieval, and eleven used the search service's retrieved page text. Fifteen excerpts date from 2026, nine from 2025, one from 2024, and two have no date. This pass did not systematically search every official, archive, transcript, or policy. It does not support claims of complete or balanced coverage.

The policy explorer includes four views: positions across policies, positions by party, statements over time, and counts of additional labels. Select a policy name in the overview to open its detail charts and source quotes.

Member bars show stance proportions among members with relevant evidence and complete assessments. The coverage column compares that count with the filtered roster. Missing evidence and incomplete assessments stay separate from stance counts. Party, member, and name filters apply to all charts. The stance filter applies only to the member list.

The timeline counts statements by month, or by quarter for longer periods. It includes empty periods between recorded statements. It excludes year-only, missing, and invalid dates and reports their count. A member can contribute several statements. These counts do not establish changes in individual views.

Detail charts distinguish final labels accepted from DeepSeek and final labels accepted after Astra review. A label can describe a detail that the speaker opposes. Expand the exact-count tables to inspect small chart segments. All charts support the page's light and dark themes and narrow screens.

The offline build writes compact records to `site/data/policy_charts.json`. A shared revision identifies matching summary and chart exports. The website rejects mismatched exports. Chart changes require no additional model calls.

### Rebuild or refresh

The policy build needs only the tracked `evidence/`, `data/roster.json`, registry, rubric, confidence instructions, strategy configuration, and `data/policy_cascade.json`. It does not need API keys or the untracked research files.

```bash
make policies-build
make serve
```

Open `http://127.0.0.1:8765/#policy-section`. The offline commands also work with standard Python 3.12 or later: `make policies-build PY=python3`. Run both test suites with `make test`; `npm test` runs the browser logic tests only.

To assess new evidence, set `OPENROUTER_API_KEY` in the environment or `.env` and use:

```bash
make policies-plan
make policies-label POLICY_ARGS="--limit-people 20 --max-cost 2"
make policies-label POLICY_ARGS="--max-cost 12"
```

The first command counts remaining work without network calls. Astra work becomes known after DeepSeek returns its scores; no fixed cost estimate assumes a review rate. The second runs a deterministic pilot. The last completes the missing assessments within an additional $12 limit and the project budget. One limit covers both stages and reserves money for concurrent requests. The default batch contains four statements because reasoning tokens share the response allowance. The provider's final accounting can differ from its published estimate. Each successful batch saves its results. Run the same command again to resume incomplete work; each invocation has its own additional limit. Run one label process at a time.

If output validation errors persist, resume with `--batch-size 1` in `POLICY_ARGS`. The parser accepts plain JSON or one fenced JSON result after provider prose. It still requires every requested statement and policy target. Incomplete responses never count as missing evidence. Shorter batches can resolve responses that exhaust their token allowance.

The label step also rebuilds the exports. The shared website build (`scripts/phase5_build_site.py`) rebuilds policy exports without paid calls. Both `make site` and the daily update use this build. The daily federal step assesses new or changed executive evidence automatically. Congressional policy assessments still need `policies-label`; their daily five-score labels use a separate system. The legacy `make refresh` pipeline also collects evidence and rebuilds the site, without paying for new policy judgments. Changed evidence, policy definitions, rubric text, confidence instructions, or model IDs invalidate the affected saved judgments. A threshold change reuses compatible assessments and recalculates which cases need Astra. A saved Astra result remains valid only for its unchanged evidence, prompts, and model.

### Add a policy or framework

Edit [`config/policies.json`](config/policies.json). Add a unique ID, title, kind (`bill`, `framework`, or `issue`), version, introduction date, official reference URL, question, search patterns, and allowed additional labels (`facets`). Use a new ID for a materially different version so the website keeps its history separate. Search patterns find candidates; the models decide relevance and stance. Use exact bill names or numbers where possible.

Run `policies-plan`, inspect the candidate coverage, run a small pilot, then run the remaining assessments. Review the source quotes and both model reasons. A new policy registry entry does not expand the search queries. Update `config/federal_sources.json` when a new policy needs a dedicated search. The daily federal step applies the policy registry to collected evidence. Congressional policy assessments still need a manual run.

The tracked judgment file retains model IDs, assessment times, generation IDs, and per-pair input hashes. The exact current instructions appear in `docs/policy-prompts-current.md`. The website exports summaries in `site/data/policies.json` and `site/data/policies.csv`, plus quotes and reasons in `site/data/policy_members/`. Policy references identify the proposals. Each quote's own link supplies the evidence for a member's position.

## Federal scores, regulation categories, and histories

[The federal analysis page](https://what-washington-says-about-ai-site.vercel.app/federal.html) covers the same current-government roster as the policy explorer. Officials and institutions remain separate. Each profile has five scores, 23 regulation categories, a cited summary, topic counts, source quotes, and monthly score history. Empty profiles remain visible with no evidence; they do not require model calls.

The five scores reuse `config/rubric.md` and the congressional fixed formula. Three DeepSeek V4.1 Flash 1017 passes assign each statement dimension labels, confidence from 1 to 5, and topics. Independent GPT-6.1 Sol review handles disagreement, confidence below 3, high catastrophic-risk or AGI labels, and large differences from the previous score. Independent Astra review handles differences of two or more levels between DeepSeek and Sol. This is the congressional daily strategy with a pinned DeepSeek model. The separate named-policy cascade still uses its 0.80 threshold.

DeepSeek and Sol each assess all 23 categories in `config/reg_focus.md`. Agreement keeps the weaker strength; direction disagreements receive independent Astra review. Summaries contain one to four sentences, each with source IDs. All judges receive the profile's evidence and attribution context. An institution's statements do not become its officials' private positions. Historical personal statements do not become an institution's position.

Every requested statement and category must receive an explicit valid response. Invalid citations and incomplete responses stay pending. Pending statement labels suppress scores; they cannot become silence zeros. As in Congress, fewer than three statements yields insufficient evidence. A completed zero for catastrophic risk, AGI, or China can mean no discussion; the interface distinguishes that from rejection. Topic totals divide each statement equally among its assigned topics.

Historical curves replay current labels over evidence dated on or before each month-end, starting in 2023. Month-only and year-only dates enter at the end of their possible interval. Undated evidence stays outside reconstructed history. These curves describe today's eligible roster, not changing government membership. Separate observed snapshots preserve the scores recorded by completed runs. Current summaries and regulation positions do not claim to describe every historical cutoff.

Caches in `data/federal_analysis_labels.json` and `data/federal_analysis_profiles.json` preserve individual model assessments, source hashes, model IDs, times, and generation IDs. Changed evidence, attribution, prompts, models, or role context invalidate affected work. Changed profile evidence also invalidates its summary and regulation assessments. Congressional caches remain separate. Public exports live in `site/data/federal_analysis.json` and `site/data/federal_analysis/`.

```bash
make federal-analysis-plan
make federal-analysis ANALYSIS_ARGS="--max-cost 5 --workers 4"
make federal-analysis-build
# A pilot or retry can select eligible profiles:
make federal-analysis ANALYSIS_ARGS="--ids exec_rudd,sisc --max-cost 2"
```

Daily collection runs the new analysis after named-policy judgments. Both stages share the existing $2 model allowance; monthly and lifetime limits also apply. Manual X workflows use the same shared allowance. The backfill command has its own invocation limit and uses the lifetime cap. Every request reserves its maximum cost against live model prices. A missing response or unknown provider cost retains the reservation. Completed assessments save immediately, and retries resume the remaining work. The ordinary site build makes no paid calls.

The older congressional cascade calibration measured agreement with model labels. It does not validate these federal results against human judgments. The named-policy confidence threshold also remains uncalibrated against human review.

## Federal historical research

The historical runner uses the same Sonnet 5.5 model as congressional web research. It makes eight separate topic and date search passes per profile. Each pass searches up to ten results. The passes cover historical statements, recent frameworks, safety, auditors, export controls, China, agency uses, and supplied source leads. A separate source pass retrieves government pages and PDF testimony. It processes the full available text in overlapping sections. When a page blocks retrieval, the runner can use independently retrieved search text. It uses the configured DeepSeek model for extraction, then verifies each excerpt against the retrieved text.

`config/federal_research_prompt.md` contains the research prompt. `config/federal_research.json` defines the model and source limits. `config/federal_research_seeds.json` records 418 source leads and unresolved role questions. The [roster source report](docs/federal-roster-sources.md) lists every profile by daily group. The [coverage audit](docs/federal-coverage-report.md) compares evidence depth with Congress and lists remaining gaps.

The runner saves paid responses and full source text locally under ignored `data/raw/federal_research/`. Public audit files contain source metadata, search effort, source failures, and added statement IDs. The runner preserves statement IDs, rejects overlapping excerpts for the same date, checks exact quote and attribution spans, and limits new quotations from non-government sources to 25 words per URL. Government speech headers can establish authorship when a quote occurs later in the document. Quote verification establishes source presence; it does not establish that every factual claim is true.

```bash
uv run python scripts/federal_research.py plan --rounds 8
uv run python scripts/federal_research.py research --rounds 8 --workers 16 --max-cost 90
uv run python scripts/federal_research.py seeds --workers 8 --max-cost 8
uv run python scripts/federal_research.py research --rounds 8 --reverify --max-cost 8
uv run python scripts/federal_research.py report
make policies-label POLICY_ARGS="--scope executive --max-cost 20"
make policies-build
```

A retry reuses its saved search result. `--refresh` makes a new paid search for the selected IDs and pass numbers. `--reverify` checks only cached search passes, although it can retrieve a missing source or format an incomplete saved result. Run the research and source passes sequentially. These one-time calls use the existing lifetime budget; daily calls also use the existing monthly cap.

The November 8 follow-up checked all 339 pending source URLs. Its [source audit](data/federal_web_completion.json) records resolved URLs, text hashes, and rejected model proposals. Source completion means the bounded review finished; it does not establish exhaustive coverage.

The site shows each profile's verified excerpt count, distinct source count, completed search passes, pending source checks, and notes from individual searches. Later passes can resolve a gap recorded in an earlier note. The coverage download compares federal people with congressional people. The current congressional median is 12 excerpts across 649 profiles. Search completion does not establish exhaustive coverage or equal evidence depth. Federal collection now selects the official X API. It still lacks the bulk govinfo channel used for Congress. No public record means no inferred stance.

### Federal X search through the official API

The federal collector uses the [official X full-archive API](https://docs.x.com/x-api/posts/search-all-posts) for account lookup and chronological search. It requires `X_BEARER_TOKEN` in the ignored local `.env` file or the workflow environment. Both federal and congressional collection use the repository secret with this name. Never commit the token or place it in command arguments.

The original repository's [November 8 run](https://github.com/harshul-basava/what-washington-says-about-ai/actions/runs/42501918942) first confirmed official archive access through the congressional collector. [PR #2](https://github.com/harshul-basava/what-washington-says-about-ai/pull/2) then merged, and four live federal batches completed all 23 configured historical account intervals. The [final historical batch](https://github.com/harshul-basava/what-washington-says-about-ai/actions/runs/42536622744) reports zero pending windows. The original repository's daily workflow remains active. The fork's duplicate daily workflow is paused. The secret stays in the original repository; forks do not inherit it.

`config/federal_x.json` links 58 sourced X handles to 50 eligible profiles through 59 ownership intervals. Of these, 51 current intervals receive daily searches. Another 47 eligible profiles lack a verified account mapping. The [X coverage report](docs/federal-x-coverage.md) lists the current mappings, ownership dates, and gaps. Historical search reached completion signals for 58 intervals. X returns `resource-not-found` for the remaining retired `MHolyoakFTC` account; it receives no daily searches.

The earlier expansion researched all 165 unmapped profiles before the user restricted coverage to current government service. Its [account research audit](data/federal_x_account_research.json) remains an archival record, including excluded profiles. The [scope archive](data/federal_scope_archive.json) identifies removed mappings and retained raw evidence. Those archived profiles no longer enter the website, judgments, or daily collectors. Eligible people retain their dated historical statements, with personal and official attribution kept separate. Existing emusks evidence retains its provenance; new searches use official X API checkpoints.

```bash
make federal-x-plan X_ARGS="--mode historical"  # offline; no authentication or writes
make federal-x X_ARGS="--mode historical --max-pages 30"
# Repeat the collection command until its pending window count reaches zero.
make policies-label POLICY_ARGS="--scope executive --max-cost 5"
make policies-build
```

Use `--ids nsa,commerce` to select profiles, or `--since YYYY-MM-DD` to set a start date. Historical searches paginate each account's permitted interval from 2023, bounded by account dates. The official cutoff is November 8, 2026, exclusive, the last complete UTC day boundary when the first run was prepared. A separate daily run covers the current period. The earlier emusks backfill retains its November 9 cutoff. Official historical queries wait until the complete interval has elapsed. Set `historical_window` to `month` for monthly intervals. A change to the account, query, interval mode, or configured dates invalidates incompatible checkpoints. Daily searches start with 14 days and then overlap previous windows by three days. The collector freezes the API end timestamp before the first page and reuses it during retries. It retains cursors even when an empty page returns another cursor.

Each invocation permits at most 200 pages, 20 minutes, and $2 in estimated additional X charges by default. The manual workflow also caps judgments at $2 and sends one model request at a time so conservative reservations can settle before the next request. `api_max_cost` controls the invocation allowance. The $150 lifetime X cap and user-approved $40 monthly daily X cap also apply, shared with Congress. The collector counts account lookups at $0.010 each and post reads at $0.005 each, per [X pricing](https://docs.x.com/x-api/getting-started/pricing). It reduces page size to fit the remaining allowance. Before each request, it records the maximum cost as a reservation in the shared ledger. A response adds a correlated adjustment for the observed count. Both records retain the request timestamp. Lost responses and interrupted requests retain their reservations with `cost_uncertain` for reconciliation. The X console remains authoritative for billing. Requests have a minimum 3.1-second interval. Rate limits preserve the server reset time and a minimum 15-minute cooldown. Incomplete runs save progress and return a failure status.

Search results can omit or truncate posts; a completed window does not establish a complete archive. The collector pins each account's numeric identity, verifies post authors and dates, and excludes reposts, advertisements, and protected content. It uses only the author's own text from quote posts. Official-role accounts have explicit date intervals. Each accepted post contributes at most 25 exact words, and duplicate post IDs retain their existing evidence. Full responses remain in ignored local storage. The existing DeepSeek/Astra cascade assesses new policy candidates; X collection itself uses no model calls.

Daily federal updates run web collection, X collection, named-policy judgments, and the federal analysis. The analysis updates the five scores, 23 regulation categories, summaries, topics, and histories. Missing X authentication produces an explicit partial status. Web collection, judgments, analysis, and selected congressional sources still run. Historical collection uses a separate command and separate checkpoints; the daily workflow does not repeat the historical backfill automatically.

The manual `Federal X collection` workflow runs one bounded batch using the original repository's secrets. It shares the daily workflow's concurrency group and saves evidence and costs even after an error. Named-policy judgments and the federal analysis share an additional $2 model allowance, then the workflow rebuilds the site. Its `historical` and `daily` modes collect X only. A successful batch can still have pending windows after a page or cost limit; inspect its report and repeat to resume. Authentication, source, and judgment errors fail the workflow. Reports live in `data/federal_x_api_historical_status.json` and `data/federal_x_api_daily_status.json`.

The first current-period pass completed all 18 active account windows across 22 successful pages and found no additional posts. Five archived accounts have no current ownership interval. Historical and daily work together cost an estimated $6.675 in X reads. The seven new excerpts produced one new policy judgment, with no pending model requests. The [aggregate run audit](data/federal_x_official_completion.json) records all five workflow runs, new evidence IDs, preserved records, costs, and daily cutoff timestamps.

```bash
gh workflow run federal-x.yml --repo harshul-basava/what-washington-says-about-ai --ref master -f mode=historical
gh workflow run federal-x.yml --repo harshul-basava/what-washington-says-about-ai --ref master -f mode=daily
```

For a manual legacy run, select `"provider": "emusks"` in `config/federal_x.json`, install dependencies with `npm ci`, and supply `X_AUTH_TOKEN`. That provider retains its separate state, session authentication, and 20-second request interval. The official provider never falls back to the session token. The default daily workflow does not install emusks or inject its session secret.

## Daily updates

A GitHub Actions job (`.github/workflows/daily.yml`) runs each day at about 6–7am Eastern. It does these steps:

1. **Collect.** It gets new statements since the last run:
   - posts on X (paid X API);
   - the Congressional Record (govinfo API), with each speaker found by their official ID;
   - hearing transcripts (govinfo API), on Mondays;
   - press releases and news, from a fixed list of sites (Exa search through OpenRouter).

   It adds each new statement to `evidence/` with a new ID. It does not change old IDs.
2. **Label.** DeepSeek labels each new statement three times. A label goes to GPT-6.1 Sol when:
   - the three runs do not agree;
   - DeepSeek's confidence is low;
   - the label is 3 or more on x-risk or AGI;
   - the label is far from the member's current score.

   GPT-6 Astra breaks ties between DeepSeek and Sol.
3. **Score.** The same fixed formula makes the new scores.
4. **Record.** It writes each score change to `data/changes.jsonl` and saves a daily snapshot in `data/history/`. A big change opens a GitHub issue. A big change is a change of 1 point or more, or a move into or out of 3+.
5. **Publish.** It rebuilds `site/data/` and pushes. Vercel then deploys the site again.

### Federal daily updates

The same job also runs `scripts/daily/federal.py`. Its source configuration lives in `config/federal_sources.json`. Each group has a topic query, an explicit domain list, and named queries derived from the registry. Each named query contains at most two profiles. A missing or duplicate agency assignment fails validation. Groups with older successful checkpoints run first. Up to four searches run concurrently within a group. A single coordinator saves all queue and query checkpoints. Official sources include the White House, NSA, Commerce, BIS, NIST, and other registered officials' agencies. Selected reporting sources help cover interviews and the White House task force. Four official pages also receive direct checks for changes. This is bounded discovery, not a complete archive crawl.

The first search requests pages from the previous 14 days. Later searches start three days before each query's last successful search. Queries with older checkpoints run first within each group. Successful queries skip repeat requests on the same day. Search providers can return older pages, and watched pages can contain older or undated statements. The collector preserves each excerpt's source date. It saves discovered URLs before extraction. Failed pages and pages beyond the six-per-group daily limit remain queued. Long pages resume at the last completed text chunk. Changed page text triggers a new extraction. Unchanged search results skip the page quota for seven days; watched pages still receive daily checks. Unchanged page text reuses the extraction result. The public state file stores source hashes and retrieval methods, without full page text.

DeepSeek extracts direct words for registered subjects. The collector requires an exact quote and an exact nearby attribution span after whitespace normalization. The span must name the subject. An explicit government speech or testimony header can establish authorship for a later quote. A model-supplied date must have a matching source date. Unknown dates remain unknown. Official-role excerpts must match a registered role title. These checks verify quote presence; they do not independently prove that the model interpreted the speaker correctly. Unverified rows stay pending for retry. Accepted excerpts retain source URLs, retrieval dates, and text hashes. Government excerpts also retain attribution spans. Copied attribution context from other sources stays in local verification files; public exports retain its hash and a short attribution summary.

The policy judge uses the configured DeepSeek V4.1 Flash 1017 model. Confidence below 0.80 triggers independent Astra review. Results below the threshold after Astra still need human review. All federal candidates use the same resumable judgment cache as manual runs. The federal collector never writes to the congressional statement log.

The default additional limits are $1.50 for collection and $2.00 for judgments per invocation. The shared monthly and lifetime caps in `budgets.yaml` also apply. Every paid call uses a `daily_` tag and checks the shared lifetime and monthly budget limits. Reservations use current model prices and conservative token bounds. Provider accounting can differ from estimates. Limits can leave work pending; the next run resumes it. Run only one collection, historical research, or policy label process at a time. Internal worker threads share a cost reservation and write checkpoints safely.

`data/federal_status.json` records each attempt, source failures, queued pages, model work, and human-review counts. The site shows the latest attempt and whether it completed. A partial update exits with failure after saving progress and rebuilding the policy exports. Federal work runs before Congress. An error in either pipeline does not prevent the other pipeline from running. The workflow commits saved progress after a failure and puts the federal report in its run summary.

```bash
make federal-dry                          # no network calls or writes
make federal                              # collect, judge, build federal policies
make federal FEDERAL_ARGS="--since 2026-10-01"
make federal FEDERAL_ARGS="--skip-collect" # resume judgments only
uv run python scripts/phase3_policies.py plan --scope executive
```

The CLI's default daily source list includes `federal`. Use `--sources federal` for a federal-only run, or an explicit list such as `--sources x,crec,web` for Congress only. The workflow runs at 11:00 UTC. On forks, an empty workflow source input selects federal-only updates; upstream keeps all daily sources. An explicit source input overrides either default. GitHub runs scheduled workflows from the default branch, so the workflow must be active there. Federal web collection and judgments use the `OPENROUTER_API_KEY` secret. Federal X search additionally requires `X_BEARER_TOKEN` in the repository that runs the workflow.

Add these repository secrets: `OPENROUTER_API_KEY`, `X_BEARER_TOKEN` and `GOVINFO_API_KEY` (free from api.data.gov). `EXA_API_KEY` is optional. If `OPENROUTER_API_KEY` is not set, the job does not run.

Monthly spend limits are in `budgets.yaml`. Before the first live run, run `make calibrate` one time (about $3–5) to set the confidence threshold.

## Limits

What a person says in public is not the same as what they believe or how they vote. AI models make the scores, and a person checks only some of them. Some members do not post much about AI, so they have little evidence.

## Credits

[CeSIA](https://cesia.org/en/data/attention/), the [@unitedstates project](https://github.com/unitedstates/congress-legislators), [GovTrack](https://www.govtrack.us/), and Zephy's earlier "What Washington Says About AGI".
