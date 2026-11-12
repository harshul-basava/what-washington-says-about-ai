# Initial evidence spot checks

The first audit found source support for 13 of 14 sampled quotations. It also found date, quotation-format, and context problems. These results do not establish an overall accuracy rate.

The audit covers six congressional statements and eight executive statements. The congressional sample uses a fixed seed of `20261112` and includes three high-score and three low-score profiles. The federal sample deliberately includes high, low, unscored, and truncated cases. Each case checks one statement, not the full profile.

Codex inspected the sources and the existing judgments. This was not a blinded review or a human validation study. The [structured audit](../data/ai_evidence_spotchecks_20261112.json) records the selection, statement IDs, hashes, checks, and review queue. The starting data came from commit `783a383679b5104d1e2b3e6ae3ab22965422802f`.

## Source checks

Ten quotations matched their original retrieved pages. Two had support in syndicated copies. One combined two supported passages from the same speaker. One original source remained unavailable. A matching source confirms quotation presence and attribution; it does not confirm the speaker's factual claims.

| Person and statement | Finding | Action |
|---|---|---|
| John Kennedy, `s29` | A syndicated USA TODAY article supports the quote. Nearby remarks connect the shutoff proposal to loss of human control. | Retain the level-3 interpretation. Record that the original URL was unavailable. |
| George Whitesides, `s26` | The office page matches the quote. Nearby text explicitly discusses existential risk. | Review the missing second-judge risk label with full context. |
| Brad Sherman, `s31` | A release mirror matches the quote. The speech ranks control-system legislation as his most important legislation. | Retain the level-4 interpretation. The office-hosted original and event date still need confirmation. |
| Tim Kaine, `s18` | A syndicated WVNS story supports both quoted segments. It does not establish a specific catastrophic scenario. | Review risk relevance and the statement date. An earlier broadcast contains similar remarks. |
| Jamie Raskin, `s2` | The source matches the quote and gives September 30 as the event date. The stored date was missing. | Add `2026-09-30`. Retain the level-2 interpretation for this excerpt. |
| Zachary Nunn, `s65` | The source supports both passages, but inserts reporter attribution between them. The event occurred one day before publication. | Correct the date to `2026-10-15`. Mark the join with an ellipsis. Retain the quoted words and labels pending any wider review. |
| Helena Fu, `s18` | Signed testimony describes AI evaluations and red teaming for weapons misuse. | Retain the level-3 interpretation under the shared catastrophe rubric. |
| Paul Christiano, `s1` | The exact excerpt warns about loss of control. The following passage calls for coordination and mitigation. | Review the excerpt boundary and the level-3 versus level-2 disagreement. |
| Michael Kratsios, `s3` | The quote matches. Neither the excerpt nor its nearby context specifies a catastrophic scenario. | Review the DeepSeek risk label of 1. Sol supplied no risk label. |
| JD Vance, `s8` | The fragment matches the X post, but ends before an example about consumer fraud. | Review the DeepSeek risk label of 1. The rubric excludes scams. |
| Donald Trump, `s1` | The official transcript supports the quote and speaker. The passage concerns competition with China. | Retain no risk label for this excerpt. |
| Ethan Klein, `s1` | The signed opening statement supports the quote, speaker, and date. It concerns international competition. | Retain no risk label for this excerpt. |
| Russell Vought, `s1` | The cited draft PDF was unavailable. A later signed memo is a different document version. | Keep this audit unresolved. The collection follow-up adds separate official sources. |
| Timothy Kosiba, `s1` | The article supports the quote, speaker, and date. A request for model access does not establish a catastrophic-risk stance. | Retain no risk label for this excerpt. |

The audit corrected two dates and marked Nunn's composite quotation with an ellipsis. It did not change model labels. The source files keep an audit reference beside each correction.

## Judgment review queue

Five sampled statements need an independent review with context: Whitesides `s26`, Kaine `s18`, Christiano `s1`, Kratsios `s3`, and Vance `s8`. The queue also includes Vance `s10`, a related truncated statement outside the original sample. That statement reports another person's risk view while criticizing political bias.

The next judge should first classify the excerpt without the existing label. It should then classify the same excerpt with the surrounding speaker context. This separates label errors from missing context. A person should resolve any remaining disagreement before score changes.

The existing Astra review of overall AI views does not review the catastrophic-risk dimension. The new federal collection received its normal model analysis and overall-view review separately. Neither process closes this risk-review queue.

## Limits and next checks

This audit does not recheck current government roles, all five score dimensions, the 23 regulation categories, summaries, or named-policy judgments. It also does not test whether the search missed important statements. The federal collection follow-up demonstrates that full government documents can contain substantial material absent from short search excerpts.

A broader validation sample should include random cases from both branches, every score range, unscored profiles, and each source type. Reviewers should check speaker identity, exact wording, event dates, context, and rubric relevance separately. Report source defects separately from classification disagreements. Keep a fixed random sample alongside targeted problem cases; targeted cases alone cannot estimate population accuracy.

The [structured audit](../data/ai_evidence_spotchecks_20261112.json) also records mechanical checks of citations, label ranges, and score calculations. These checks test data consistency. They cannot establish that a model interpreted a statement correctly.

## Collection follow-up and validation

The follow-up added 16 verified excerpts from five source documents. Klein gained eight excerpts, Vought gained six, and Danly and Cossa each gained one. The full-source checks recovered material from hearings and signed government memoranda.

All new excerpts completed the normal model analysis. Astra reviewed overall AI views for all four profiles. Klein and Vought now score 3 for overall AI views. Danly has a China-competition score of 2.5. Cossa still has only two statements, below the three-statement minimum. These profiles retain their daily search assignments.

The additional model cost was $0.635063. The follow-up made no paid X calls. The combined limit remained $8. The [collection audit](../data/federal_collection_followup_20261112.json) records each excerpt, its source, and the completed workflow runs.

The site build passed, along with 298 Python tests and 64 JavaScript tests. Independent arithmetic checks matched all 5,920 score cells across the 649 congressional roster records and 535 federal profiles. Citation checks found no missing statement IDs among 7,238 references. These counts include congressional roster records beyond the current Congress. They describe structural consistency, not interpretation accuracy.
