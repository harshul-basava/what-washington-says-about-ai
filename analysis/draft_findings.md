# Draft findings (for Harshul to edit)

All numbers come from `analysis/headline_numbers.json`, which `analysis/build_notebook.py` regenerates. Figures are in `analysis/figures/`. These are **pre-review** numbers: Phase 4 human review hasn't happened yet, so treat every named example as provisional until it's checked against `review/review_packet.md`.

## Coverage
- 649 people: 539 current members and 110 members-elect from called 2026 races. 15,481 statements in total, all of them either verified quotes or the members' own X posts: 9,005 X posts, 3,554 web quotes, 2,568 hearing quotes, 340 floor speeches and 14 official statements.
- 533 of 539 current members said *something* about AI on the record since 2023. The median member has 15 AI statements. Lieu (404), Hawley (293), Sanders (265) and Khanna (257) have the most.
- About 6% of statements (953) are "untagged". These are mostly X posts that were thinned out of the scoring input for the heaviest posters, who were capped at 150 statements each.

## Partisanship is the dominant axis, except on AGI
- **Optimism (`ai_overall`):** Republicans average 2.73 and Democrats 1.65 (0 = very concerned, 4 = very optimistic). 73% of scored Republicans are "mostly or very optimistic" (score ≥3), against 7% of Democrats. Spearman ρ with GovTrack ideology = 0.66.
- **Regulation:** this is the mirror image. Democrats average 2.95 and Republicans 1.61. 76% of Democrats vs. 6% of Republicans support substantial rules (score ≥3). ρ with ideology = −0.66.
- **China race:** 61% of Republicans use beating China as a primary lens (score ≥3), against 11% of Democrats. ρ = 0.56.
- **AGI-pilledness is *not* partisan:** ρ with ideology = −0.01. Party means are D 2.05 and R 1.97. Scoring this needs explicit statements, so 210 current members (about 40%) lack the evidence for an AGI score at all.

## AGI and existential risk are still fringe, and lopsided toward Democrats
- **x-risk:** 86 current members (16%) acknowledge loss of control or existential risk as a real concern (score ≥3): 71 Democrats, 12 Republicans and 3 independents. 15 treat it as a top-tier priority (score 4). Among those 15, Andy Harris (R-MD) is the only Republican.
- **AGI:** 41 current members (8%) treat AGI or superintelligence as a real near-to-medium-term possibility (score ≥3). Only 5 make it central (score 4). 34 members clear the ≥3 bar on both AGI and x-risk.
- **Most AGI-pilled (≥3.5):** Sanders, Sherman, Kiley, Luna, Casar and Ansari. This group cuts across party, which matches the zero correlation with ideology.

## Topics over time (shares of statements, 2023 → 2026)
- **Energy and data centers** rose from about 0% to 10% of AI statements, the biggest shift. It began in 2025-Q1 and is still climbing.
- **Jobs and the economy** rose from 7% to 12%. **China** rose from 5.5% to 8%.
- **Deepfakes and elections** fell from 7% to 3%. **Copyright** fell from 3.4% to 0.7%.
- **x-risk / loss of control** ran at about 2–3% in 2023 and under 1% through 2024–2025, then **spiked to about 9% in 2026-Q3**. That came from 483 tagged statements, overwhelmingly Democratic (Lieu, Liccardo, Casar, Ansari, Trahan, Sanders…). Many mention a pause, "superintelligence" and Trump, which points to a coordinated reaction to a news event. **TODO: identify the event before writing this up.**
- Over the whole period, the x-risk share among Democrats roughly tripled (2.3% → 6.5%). Among Republicans it barely moved (2.1% → 2.6%).

## Members-elect
- Members-elect (mostly Democrats) are more pro-regulation than the current Congress (2.77 vs. 2.29), less optimistic (1.52 vs. 2.20) and less China-focused (1.62 vs. 2.22). Four of the 19 people with an x-risk score of 4 are members-elect: Scott Wiener, William Lawrence, Sam Forstag and Abdul El-Sayed.
- **Caveat:** the incoming class is 83 D vs. 27 R among called races so far, so these differences mostly reflect party composition.

## Robustness
- The two independent, shuffled scoring runs agree exactly on 91% of person-dimension pairs and never differ by more than 1 point.
- Rank correlation with Roe's January 2026 scores is moderate: ρ = 0.31 (AGI), 0.32 (x-risk) and 0.48 (China). This is expected, because the methods differ (all verified statements vs. 10 researched quotes, a 0–4 rubric vs. 0–100). The biggest disagreements are listed in `review/roe_comparison.md` and are worth a look before publishing.

## Caveats to state in the post
- The volume of statements over time is shaped by collection. X starts in 2023. Web research favors recent, prominent statements. The congressional record lags. 2026-Q4 is partial. Use **shares**, not counts.
- X recall: the first 132 people were collected through a free unofficial client, which found about 94% of the posts the paid API found in a spot test. Everyone else was collected through the paid full-archive API. Handles were validated by checking the profile name of each post's author.
- Scores measure **what people say publicly**, not how they vote or what they privately believe. "Insufficient evidence" is common on AGI (about 40%) and China (about 30%).
- All scoring was done by a single model family (Claude Sonnet 5.5), and human review (Phase 4) is pending.
