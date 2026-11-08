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
