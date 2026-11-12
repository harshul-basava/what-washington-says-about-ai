# Efficient federal collection campaign

The campaign reuses official documents, search responses and valid judgments. It preserves the current quote, attribution, date, role and duplicate checks. It also preserves three DeepSeek label passes, Sol/Astra escalation, regulation judgments and independent Astra stance reviews.

## Budget and execution

The user authorized the new budget on November 12, 2026. A read-only check found $119.483081 of provider allowance. The repository's previous $500 lifetime ceiling left $45.873511. The authorized update sets that ceiling to $600. Provider and daily/monthly limits remain unchanged.

The campaign has a fixed $100 cumulative model allowance. Its $3 trial counts inside that allowance. Collection and discovery share a $20 ceiling. The remaining funds support judgments and context review. The campaign reserves at least $20 of remaining model allowance before further collection. X uses a separate $5 cumulative ceiling inside the existing X project limit. Historical X searches retain their original intervals and cursors.

The [campaign configuration](../config/federal_collection_campaign.json) records the fixed limits. The [implementation plan](superpowers/plans/2026-11-12-federal-efficient-collection.md) records the verification gates. The manual workflow shares the daily job's concurrency group. This prevents simultaneous writers from spending against separate ledger snapshots.

`uv run python scripts/federal_collection_campaign.py plan` is offline. The original repository's `Efficient federal collection` workflow supplies credentials for `run --phase trial` and `run --phase expand`. Expansion requires a successful trial. Retries retain the original ledger baseline and evidence IDs.

## Collection and reuse

The configured inventory covers 41 index pages, plus existing official sources and source leads. Source groups include the White House, Federal Reserve, Commerce/NIST, Energy, Justice, Treasury, SEC, FTC, CIA, NSA, CISA and ODNI. Some indexes block direct retrieval. The report records those gaps; an index entry does not prove successful collection.

Eight workers retrieve documents. Four extraction requests can run at once through one budget manager. A lock serializes evidence updates. The queue rotates source groups and preserves priority within each group. Multi-speaker hearings without reviewed speaker mappings receive no extraction request because their quotes cannot pass the existing verifier.

Each extraction signature includes the source, subjects, prompt and model. Search signatures include the complete prompt, model, domain restrictions and date window. Empty and malformed responses remain in the cache. Changed inputs invalidate their results. Daily and campaign workflows share one cache prefix and the same path list.

After archive work, the campaign searches for officials with fewer than three excerpts. It pairs names within each agency and rotates agencies. It checks existing verified X accounts only where evidence remains sparse. It does not invent account mappings or add former officials.

Ordinary judgments reuse unchanged statement inputs. Full-profile regulation and summary judgments update when their evidence changes. Astra reuses a compatible completed profile audit. Changed evidence or context still requires review. Every request includes each full source text once, with separate excerpt references and attribution metadata.

## Completion and limits

The trial targets five officials across five agency groups. The wider campaign has explicit document, query and excerpt bounds. These bounds make the run reviewable and prevent cheap extraction from creating an unaffordable judgment backlog. They do not establish complete federal coverage.

Failed queries, incomplete extractions, pending X intervals and unfinished model judgments remain pending. Confirmed retrieval failures remain visible as source gaps. Unavailable evidence never becomes a neutral or opposing stance.

The final report will record actual spend, accepted excerpts, unique sources, officials and agencies reached, source gaps and remaining budget. The workflow saves public progress on failure and retains raw verification material in its cache. Full raw documents, credentials and the local human review tool stay outside Git.

## Trial recovery and source checks

The first trial checked 120 documents and spent $0.006130. It added no evidence, so the expansion gate stopped the campaign. The queue included many documents unrelated to the five selected officials. The corrected queue prioritizes their agency domains and known source leads, while retaining other documents. The trial permits 240 document checks in total. Its original $3 model limit and campaign baseline remain unchanged.

The SEC publishes speaker names in a dedicated news-speaker field. The parser now recognizes a single commissioner link inside that field on a standalone SEC speech page. The verifier requires the exact header, supported URL, and matching person. Generic page names, unrelated domains and joint speaker fields do not establish authorship. This uses the same standard as the existing Federal Reserve speaker parser.

Treasury document patterns now accept trailing slashes. ODNI uses its current newsroom and numbered document URLs. Index checkpoints include their source configuration, so a corrected pattern invalidates an empty cached result. Justice's HTTP 200 access-challenge page now records a source gap instead of a completed empty archive. The collector does not bypass the challenge.

Interrupted documents remain retryable after the document quota. Saved discovery results also remain pending until their queued extraction finishes or a source failure is recorded. Retries preserve all cost baselines and completed model responses.

A read-only budget check at 07:11 UTC found $123.266063 in account credit, $119.476951 in provider allowance and $145.867381 under the repository ceiling. The campaign uses the lowest applicable allowance and checks it again before each invocation.

## Completed trial

The resumed trial completed on November 12. The full trial cost $0.241143 in model calls and $0.005 in X context retrieval. It added six verified excerpts from one SEC speech by Paul S. Atkins. All 18 existing and new excerpts in his profile completed ordinary analysis. Named-policy work had no pending requests. Independent Astra review completed without an outstanding context request.

The source replay verified all six new excerpts without model calls. A separate retrieval of the SEC page repeated the quote, author and date checks successfully. The trial checked five officials, but only one supplied new evidence. Its cost does not establish expected productivity across other agencies.

The wider campaign began with $99.758857 of its model allowance remaining. The X allowance had $4.995 remaining. The final audit now also replays the existing web attribution, date and role validator against retained source snapshots. The workflow's `verify` phase makes no paid calls.

## Local source-processing benchmark

The collector now checks which names are possible before it runs the existing exact matcher. The check preserves optional middle initials, aliases, Unicode case matching and reviewed transcript speaker mappings. Non-ASCII names bypass the candidate filter. The exact matcher still decides every accepted name match. Extraction requests and cache signatures remain unchanged.

On one 134,445-character official hearing transcript, matching the 500 officials took 1.21 seconds before the change and 0.035 seconds afterward. Both methods matched the same three profiles. This is a local name-matching benchmark, not a claim that the complete research pipeline runs 35 times faster.

## Reviewed transcript speaker context

The extraction prompt referred to reviewed speaker mappings, but its subject payload omitted them. The corrected payload includes only mappings bound to the current source URL. The existing source, identity, date and same-speaker-turn checks remain unchanged. This affects seven registered source URLs for Jerome H. Powell and Jules W. Hurst III.

Only extraction caches for bound speaker sources receive a new signature. Other source signatures remain unchanged. The next campaign resume will recheck the affected sources under the original spending limits, if collection allowance remains. It then updates judgments for any new evidence. A missing allowance records the deferred source URLs explicitly. Fresh campaigns still perform archive discovery before this migration.

## Same-source duplicate corrections

The resume audit found repeated quotations from the same source with different date metadata. The collector now rejects an identical normalized quotation from the same canonical URL, regardless of that metadata. Statements from different sources and dates retain the existing rules.

Ten campaign records now carry `duplicate_of` references to their earlier stable IDs. The records remain on disk for audit. Analysis, public counts, and campaign addition counts exclude them. The comparison ignores a copied terminal comma, but preserves question marks and the original quotation text. The loader rejects a correction unless both records have the same source and quotation. It also rejects missing targets, self-references, and chains. Original quotations, dates, attribution, and IDs remain unchanged. The correction report lives in `data/federal_collection_duplicate_corrections.json`.

## November 12 expansion checkpoint

Run 43195230024 completed web collection, ordinary analysis, named-policy judgments, and independent Astra review for 52 changed profiles. Its source replay checked 435 additions from 160 sources. The subsequent terminal-comma correction reduces the active additions to 434. The affected profile will complete review again before the campaign finishes.

Cumulative model spending reached $20.543324, leaving $79.456676 under the original $100 allowance. Collection and discovery account for $2.657826 of that total. X spending reached $0.305 under its separate $5 ceiling. Six historical X intervals remain pending. The workflow correctly retained a pending campaign status and saved its evidence, judgments, costs, and caches.

The checkpoint reached 262 officials with evidence, compared with 261 at the campaign baseline. Most additions deepen existing profiles. The archive inventory also contains hearing transcripts that require reviewed speaker mappings. Those sources remain excluded from personal evidence until the same identity and speaker-turn checks can pass. Further work will assess these gaps within the original allowance.
