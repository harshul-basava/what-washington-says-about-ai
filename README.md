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

## Limits

What a person says in public is not the same as what they believe or how they vote. AI models make the scores, and a person checks only some of them. Some members do not post much about AI, so they have little evidence.

## Credits

[CeSIA](https://cesia.org/en/data/attention/), the [@unitedstates project](https://github.com/unitedstates/congress-legislators), [GovTrack](https://www.govtrack.us/), and Zephy's earlier "What Washington Says About AGI".
