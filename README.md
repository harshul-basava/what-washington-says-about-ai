# What Washington Says About AI

This project tracks what each member of Congress says in public about AI. It also covers the new members elected in 2026.

Each person gets a score from 0 to 4 on five questions:

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

The label step also rebuilds the exports. The shared website build (`scripts/phase5_build_site.py`) rebuilds policy exports without paid calls. Both `make site` and the daily update use this build. New or changed evidence appears as pending until a manual `policies-label` run assesses it. The legacy `make refresh` pipeline also collects evidence and rebuilds the site, without paying for new policy judgments. Changed evidence, policy definitions, rubric text, confidence instructions, or model IDs invalidate the affected saved judgments. A threshold change reuses compatible assessments and recalculates which cases need Astra. A saved Astra result remains valid only for its unchanged evidence, prompts, and model.

### Add a policy or framework

Edit [`config/policies.json`](config/policies.json). Add a unique ID, title, kind (`bill`, `framework`, or `issue`), version, introduction date, official reference URL, question, search patterns, and allowed additional labels (`facets`). Use a new ID for a materially different version so the website keeps its history separate. Search patterns find candidates; the models decide relevance and stance. Use exact bill names or numbers where possible.

Run `policies-plan`, inspect the candidate coverage, run a small pilot, then run the remaining assessments. Review the source quotes and both model reasons. A new registry entry does not collect new statements. Refresh the upstream evidence separately when a new policy appears. Updates require a manual run; this feature does not add a schedule.

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

Add these repository secrets: `OPENROUTER_API_KEY`, `X_BEARER_TOKEN` and `GOVINFO_API_KEY` (free from api.data.gov). `EXA_API_KEY` is optional. If `OPENROUTER_API_KEY` is not set, the job does not run.

Monthly spend limits are in `budgets.yaml`. Before the first live run, run `make calibrate` one time (about $3–5) to set the confidence threshold.

## Limits

What a person says in public is not the same as what they believe or how they vote. AI models make the scores, and a person checks only some of them. Some members do not post much about AI, so they have little evidence.

## Credits

[CeSIA](https://cesia.org/en/data/attention/), the [@unitedstates project](https://github.com/unitedstates/congress-legislators), [GovTrack](https://www.govtrack.us/), and Zephy's earlier "What Washington Says About AGI".
