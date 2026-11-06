# Draft findings (for Harshul to edit)

All numbers come from `analysis/headline_numbers.json`, which `analysis/build_notebook.py` regenerates. Figures are in `analysis/figures/`. Scores use **rubric v2** and have been reviewed by a second model family (see "Robustness"). Treat named examples as provisional until you've checked them against `review/crossmodel_report.md`.

## Coverage
- 649 people: 539 current members and 110 members-elect from called 2026 races. There are 15,481 statements in total, all of them verified quotes or the members' own X posts: 9,005 X posts, 3,554 web quotes, 2,568 hearing quotes, 340 floor speeches and 14 official statements.
- 533 of 539 current members said *something* about AI on the record since 2023. The median member has 15 AI statements. Lieu (404), Hawley (293), Sanders (265), Khanna (257) and Klobuchar (243) have the most.

## Party drives most views, except on AGI
- **Optimism (`ai_overall`):** Republicans average 2.71 and Democrats 1.66 (0 = very concerned, 4 = very optimistic). 69% of scored Republicans are mostly or very optimistic, against 5% of Democrats. Rank correlation with GovTrack ideology: ρ = 0.66.
- **Regulation:** the mirror image. Democrats average 2.89 and Republicans 1.65. 70% of Democrats back substantial rules, against 6% of Republicans. ρ = −0.64.
- **China race:** 60% of Republicans treat beating China as a main lens, against 10% of Democrats. ρ = 0.54.
- **Expecting AGI is barely partisan:** ρ with ideology is −0.12, and the party means are D 2.18 and R 2.01. Most members never say anything about how big AI's impact will be, so about 45% of current members don't have enough evidence for an AGI score.

## AGI and existential risk are still minority views, and mostly Democratic ones
- **Loss of control:** 103 current members (19%) treat loss of control or existential risk as a real concern (score 3+): 82 Democrats, 18 Republicans and 3 independents. 17 treat it as a top priority (score 4). Andy Harris (R-MD) is the only Republican among them.
- **AGI:** 37 current members (7%) see AGI or superintelligence as a real near- or medium-term possibility. 5 make it central. 31 members are at 3 or above on both AGI and loss of control.
- **Most AGI-focused (3.5 or above):** Sanders, Lynch, Sherman, Kiley, Casar and Ansari.

## Topics over time (share of statements, 2023 → 2026)
- **Energy and data centers:** from almost nothing (0.4%) to 10% of AI statements, the biggest shift. It started in 2025-Q1.
- **Jobs and the economy:** 7% → 11%. **China:** 5% → 8%.
- **Falling:** deepfakes and elections 7% → 3%; copyright 3.5% → 0.7%.
- **Loss of control / x-risk:** about 2–3% of statements in 2023 and under 1% through 2024–2025, then a spike to about 9% in 2026-Q3. The spike is concentrated in **September 9–17, 2026**. Going only by what members themselves said at the time, it followed a cluster of events: an Anthropic safety researcher resigning with a public warning, and a colleague putting the odds of AI killing all humans above 10%; an "OpenAI/Hugging Face incident" in which a model reportedly escaped its sandbox (members cite a METR report on it); the OpenAI and Anthropic CEOs warning the following week; and the President calling the concern a hoax. Members responded with calls for a 30-day "safety stand-down", the AI Kill Switch Act, and a letter urging the Speaker to keep the House in session. Reactions were overwhelmingly Democratic, but not entirely: some Republicans (e.g. Roy) voiced concern, while others argued against slowing down because of China. **Check these events against news coverage before publishing; they are reconstructed from members' statements, not verified independently.**
- **By party:** the x-risk share among Democrats tripled (2.3% → 6.9%). Among Republicans it barely moved (1.9% → 2.8%).

## The Congress that takes office in January 2027
- With called races only, the next Congress has **26 more members who back substantial AI rules** (183 → 209), **53 fewer AI optimists** (184 → 131) and **41 fewer members who frame AI mainly as a race with China** (148 → 107) than today's. Loss-of-control concern (103 → 102) and AGI expectations (37 → 34) are about flat. Worth re-checking once the remaining 38 races are called.
- Members-elect (mostly Democrats) are more pro-regulation than the current Congress (2.74 vs 2.28), less optimistic (1.58 vs 2.18) and less China-focused (1.62 vs 2.18).
- Five members-elect score 4 on loss of control: Scott Wiener, William Lawrence, Sam Forstag, Abdul El-Sayed and Melat Kiros.
- **Caveat:** the incoming class is 83 Democrats and 27 Republicans among called races, so much of this is party composition.

## Robustness
- **Two scoring runs:** with the statements shuffled differently, they agree exactly on 90% of person-question pairs. Only 4 pairs differ by 2 points or more, and those are flagged.
- **A second model family** (OpenAI's GPT-6.1 Sol) re-scored everyone blind. Rank agreement is ρ = 0.84–0.90 on four of the five questions, with 98–100% of members within 1 point. AGI is lower, at ρ = 0.66. Rubric v2 cut the cases where only one model thought there was enough evidence: AGI from 192 to 77, China from 159 to 25.
- **Audit:** the reviewer audited 49 hard cases (the top scorers, a random sample, and every case where the two models disagreed). It disagreed on 18% of person-questions. In 11% of them, none of the cited quotes supported the score. These cases are listed by name in `review/crossmodel_report.md` and are worth a human look before publishing.
- **Comparison with Roe's January 2026 scores:** moderate agreement, ρ = 0.27 (AGI), 0.33 (x-risk) and 0.47 (China). The methods differ a lot: all verified statements and a 0–4 rubric here, against 10 researched quotes on a 0–100 scale. The biggest disagreements are in `review/roe_comparison.md`.

## Caveats to state in the post
- Statement counts over time are shaped by how the data was collected: X starts in 2023, web research favors recent and prominent statements, the congressional record lags, and 2026-Q4 is partial. Use **shares**, not counts.
- X recall: the first 132 people came from a free unofficial client, which found about 94% of the paid API's posts in a spot test. Everyone else came from the paid full-archive API.
- Scores measure **what people say publicly**, not votes or private beliefs. Only the member's own stated views count; quoting someone else's warning doesn't.
- Scoring is by Claude Sonnet 5.5 and checked by GPT-6.1 Sol. No human has hand-checked every score.
