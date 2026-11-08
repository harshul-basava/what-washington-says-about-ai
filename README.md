# What Washington Says About AI

This project tracks public statements about AI from Congress, executive officials, and federal institutions. The congressional roster also covers new members elected in 2026.

The congressional view gives each person a score from 0 to 4 on five questions. Executive and institutional profiles use the policy judgments below:

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
3. **Label.** Two AI models (Claude Sonnet 5.5 and GPT-6.1 Sol) each read every statement. Each model gives a level for each question that the statement addresses. The rules for each level are in [`config/rubric.md`](config/rubric.md).
4. **Score.** A fixed formula changes the labels into a score for each person. The published score is the average of the scores from the two models.
5. **Review.** A person checks the scores where the two models do not agree.

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

The explorer has separate Congress, Executive officials, and Institutions views. The initial federal collection contains 13 officials, eight institutions, and 27 verified excerpts. It covers the White House, Commerce, BIS, NIST, CAISSI, NSA, its security center, and the White House Superintelligence Task Force. This is curated coverage, not a complete federal census. Andrew Ferguson has sourced roles but no personal policy quote in this initial collection.

An agency filter includes its subagencies and linked roles. Each person counts once, even with several appointments. Executive and institution charts group profiles by their primary organization. Congressional charts retain party grouping. The views never combine people and institutions in one denominator. Profile links connect officials and institutions. Source statements remain available even when none matches the selected policy.

The additional registry lives in `config/policy_subjects.json`. It records institution relationships, dated roles, aliases, and membership sources. Unknown start and end dates remain unknown. A role source can describe a historical appointment; its check date does not establish current service. Task-force membership includes clearly marked reporting sources. The White House Super Intelligence Force is separate from the Justice Department's task force. Historical sources may use CAISI/AISI or AISC; the current institutional pages use CAISSI and SISC.

Every new statement records attribution as `personal`, `official_role`, or `institutional`. Named officials' statements belong to their profiles. Institutional and joint statements do not propagate to members. The model receives attribution and role context. Changes to attribution invalidate that statement's judgment. The unchanged congressional candidates retain their existing cache hashes.

To extend federal coverage, edit the registry and add verified, stable `s1`, `s2`, etc. statements to `evidence/<subject-id>.json`. Match each excerpt against the source text, record its retrieval method, date, and text hash, and update `config/policy_source_manifest.json`. This collection uses exact matching after whitespace normalization. Where direct retrieval failed, verification used the search service's retrieved page text. This checks quote presence, not the source's factual claims or transcript accuracy. Do not reassign existing statement IDs or copy one collective statement into each member's file. Run `make policies-plan`, `make policies-label POLICY_ARGS="--max-cost 2"`, then `make policies-build`. A registry-only profile needs an explicit empty evidence file.

The daily job now searches federal sources and assesses new federal policy evidence. It covers the registered executive officials and institutions in four source groups: the executive branch, Commerce and its agencies, NSA and its security center, and the White House Superintelligence Task Force. The five-score charts still cover Congress only. Role and membership changes need manual review.

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

The same job also runs `scripts/daily/federal.py`. Its source configuration lives in `config/federal_sources.json`. Each group has two search queries and an explicit domain list. Official sources include the White House, NSA, Commerce, BIS, NIST, and other registered officials' agencies. Selected reporting sources help cover interviews and the White House task force. Four official pages also receive direct checks for changes. This is bounded discovery, not a complete archive crawl.

The first search requests pages from the previous 14 days. Later searches start three days before each group's last successful search. Search providers can return older pages, and watched pages can contain older or undated statements. The collector preserves each excerpt's source date. It saves discovered URLs before extraction. Failed pages and pages beyond the six-per-group daily limit remain queued. Long pages resume at the last completed text chunk. Changed page text triggers a new extraction. Unchanged search results skip the page quota for seven days; watched pages still receive daily checks. Unchanged page text reuses the extraction result. The public state file stores source hashes and retrieval methods, without full page text.

DeepSeek extracts direct words for registered subjects. The collector requires an exact quote and an exact nearby attribution span after whitespace normalization. The span must name the subject. A model-supplied date must have a matching source date. Unknown dates remain unknown. Official-role excerpts must match a registered role title. These checks verify quote presence; they do not independently prove that the model interpreted the speaker correctly. Unverified rows stay pending for retry. Source URLs, attribution spans, retrieval dates, and text hashes remain attached to accepted excerpts.

The policy judge uses the configured DeepSeek V4.1 Flash 1017 model. Confidence below 0.80 triggers independent Astra review. Results below the threshold after Astra still need human review. All federal candidates use the same resumable judgment cache as manual runs. The federal collector never writes to the congressional statement log.

The default additional limits are $0.50 for collection and $2.00 for judgments per invocation. Every paid call uses a `daily_` tag and checks the shared lifetime and monthly budget limits. Reservations use current model prices and conservative token bounds. Provider accounting can differ from estimates. Limits can leave work pending; the next run resumes it. Run only one daily or policy label process at a time.

`data/federal_status.json` records each attempt, source failures, queued pages, model work, and human-review counts. The site shows the latest attempt and whether it completed. A partial update exits with failure after saving progress and rebuilding the policy exports. Federal work runs before Congress. An error in either pipeline does not prevent the other pipeline from running. The workflow commits saved progress after a failure and puts the federal report in its run summary.

```bash
make federal-dry                          # no network calls or writes
make federal                              # collect, judge, build federal policies
make federal FEDERAL_ARGS="--since 2026-10-01"
make federal FEDERAL_ARGS="--skip-collect" # resume judgments only
uv run python scripts/phase3_policies.py plan --scope executive
```

The default daily source list includes `federal`. Use `--sources federal` for a federal-only run, or omit it for a congressional-only run. The workflow still runs at 11:00 UTC. GitHub runs a scheduled workflow from the repository's default branch, so the new federal step starts after this change merges there. It uses the existing `OPENROUTER_API_KEY` secret and does not need a new service or key.

Add these repository secrets: `OPENROUTER_API_KEY`, `X_BEARER_TOKEN` and `GOVINFO_API_KEY` (free from api.data.gov). `EXA_API_KEY` is optional. If `OPENROUTER_API_KEY` is not set, the job does not run.

Monthly spend limits are in `budgets.yaml`. Before the first live run, run `make calibrate` one time (about $3–5) to set the confidence threshold.

## Limits

What a person says in public is not the same as what they believe or how they vote. AI models make the scores, and a person checks only some of them. Some members do not post much about AI, so they have little evidence.

## Credits

[CeSIA](https://cesia.org/en/data/attention/), the [@unitedstates project](https://github.com/unitedstates/congress-legislators), [GovTrack](https://www.govtrack.us/), and Zephy's earlier "What Washington Says About AGI".
