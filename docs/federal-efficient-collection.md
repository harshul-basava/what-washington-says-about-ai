# Efficient federal collection campaign

The campaign reuses official documents, search responses and valid judgments. It preserves the current quote, attribution, date, role and duplicate checks. It also preserves three DeepSeek label passes, Sol/Astra escalation, regulation judgments and independent Astra stance reviews.

## Budget and execution

The user authorized the new budget on November 12, 2026. A read-only check found $119.483081 of provider allowance. The repository's previous $500 lifetime ceiling left $45.873511. The authorized update sets that ceiling to $600. Provider and daily/monthly limits remain unchanged.

The campaign has a fixed $100 cumulative model allowance. Its $3 trial counts inside that allowance. Collection and discovery share a $20 ceiling. The remaining funds support judgments and context review. The campaign reserves at least $20 of remaining model allowance before further collection. X uses a separate $5 cumulative ceiling inside the existing X project limit. Historical X searches retain their original intervals and cursors.

The [campaign configuration](../config/federal_collection_campaign.json) records the fixed limits. The [implementation plan](superpowers/plans/2026-11-12-federal-efficient-collection.md) records the verification gates. The manual workflow shares the daily job's concurrency group. This prevents simultaneous writers from spending against separate ledger snapshots.

`uv run python scripts/federal_collection_campaign.py plan` is offline. The original repository's `Efficient federal collection` workflow supplies credentials for `run --phase trial` and `run --phase expand`. Expansion requires a successful trial. Retries retain the original ledger baseline and evidence IDs.

## Collection and reuse

The configured inventory covers 172 index pages or public data files, plus existing official sources and source leads. Source groups include the White House, Federal Reserve, Commerce/NIST, Energy, Justice, Treasury, SEC, FTC, CIA, NSA, CISA and ODNI. Some indexes block direct retrieval. The report records those gaps; an index entry does not prove successful collection.

Eight workers retrieve documents. Eight extraction requests can run at once through one budget manager. A lock serializes evidence updates. The queue rotates source groups and preserves priority within each group. Multi-speaker hearings without reviewed speaker mappings receive no extraction request because their quotes cannot pass the existing verifier.

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

## Completed first expansion wave

Run 43208756264 finished the six remaining X intervals and the affected profile review. All 434 active additions from 159 sources passed the full source replay. All 52 changed profiles completed ordinary analysis, named-policy judgments and independent Astra review. The X searches added no statements.

Cumulative model spending reached $21.501196, leaving $78.498804 under the original allowance. Collection and discovery account for $2.657826 of that total. Separate X spending reached $0.365. The campaign now resumes from this completed checkpoint without resetting its baseline, caches or limits.

## Reviewed hearing expansion and deeper archives

The next wave adds 47 source-specific speaker mappings for 37 current officials across 42 official hearing documents. The assistant checked each identity, exact oral label and hearing date against the primary source. The audit lives in `data/federal_hearing_speaker_review.json`. One candidate mapping incorrectly connected Representative French Hill's words to FDIC official Travis Hill. The review rejected it.

GPO transcripts use indented, mixed-case speaker labels. The parser retains the original preformatted lines and requires the exact indentation before it accepts a mapped speaker. Unknown speakers and section headings end the previous turn. Written answers do not inherit the oral hearing date. Source URL, person, date and same-turn checks remain mandatory. Unsupported formats remain gaps. Daily collection uses the same parser and invalidates cached results when line proof changes.

Historical testimony can precede an official's current appointment. The source mapping establishes personal identity; it does not establish that the official held the current role on the statement date. Existing role checks still apply.

Free archive discovery added 1,536 source leads across NIST, Energy, FTC, SEC and Treasury. These leads increase the inventory to 3,557 documents. Deeper SEC discovery uses only chronological page links. Treasury's public page code loads older records from JSON files. The collector now reads those files directly, covering press releases since 2025 and remarks since 2023. Index dates select leads only; every accepted statement must still pass the article's full verification checks.

The new indexes also feed daily updates. `data/federal_archive_extension.json` records the source URLs and discovery counts. These counts describe leads, not accepted statements. The original campaign's collection and review limits remain unchanged.

## Completed X search reuse

The official X planner now reuses a completed account search when its saved interval fully covers the requested interval. Reuse requires the same account and query fingerprint, a terminal cursor, at least one saved page and a sufficient actual query cutoff. It retains the original checkpoint. Pending cursors, changed account definitions and incomplete cutoffs remain pending. Daily searches retain their separate checkpoints.

The current roster plan initially showed 40 pending intervals. Saved records prove that 39 already have completed searches through a later cutoff. Only one historical interval remains incomplete. The campaign can now check all mapped current officials within its saved roster, while retaining the original X allowance. A changed selection reopens the X stage. An older completed result cannot hide a new pending plan when funds are insufficient.

Eight extraction requests now share the existing budget manager. Evidence writes remain serialized. Ordinary analysis retains four workers; expensive reviews retain two. The regression suite checks simultaneous writes to the same profile and the shared chunk limit. These changes do not alter prompts, models, source checks or spending caps.

## Completed hearing and Treasury wave

Run 43213184419 completed successfully and saved commit `f7335de0`. Cumulative additions reached 710 verified excerpts from 236 sources across 71 officials. All required ordinary analysis, named-policy work and independent Astra reviews finished. The source replay passed every addition. Twelve fresh primary-source checks also passed, including six hearings. Their context notes appear in `data/federal_collection_expansion_spotcheck.json`. These targeted checks do not establish a population accuracy rate.

Cumulative model spending reached $37.144734, leaving $62.855266. Collection and discovery account for $4.287314 of that total. Separate X spending reached $0.435. Evidence coverage reached 263 of 500 current officials. Most additions deepen existing profiles.

The next batch adds 241 candidate documents after 1,089 free public-source checks. It extends health, science, procurement, labor, agriculture and banking archives. The 106 added index pages bring the configured total to 172. Candidates still require the full existing verification process. The source inventory and selection details appear in `data/federal_archive_followup.json`.

The expanded audit also found 13 repeated source quotations that predate this campaign. Their records remain on disk with validated `duplicate_of` references. The next review refresh excludes their duplicate counts. This correction does not reduce the 710 new campaign excerpts. The original cost baselines and limits remain unchanged.

## Follow-up archive results and X availability gap

Run 43235810637 added 25 excerpts. Cumulative additions reached 735 excerpts from 257 sources across 74 officials. Ordinary analysis, named-policy judgments, independent Astra reviews and local source replay all completed. The corrected duplicate counts leave 3,753 excerpts for officials and 5,730 across all federal profiles. Coverage remains 263 of 500 current officials.

The workflow retained a pending result because the official X API could not find `@MHolyoakFTC`. Its response reported `lookup_response_errors` and `resource-not-found`. All other mapped officials had no pending planned historical interval. The explicit source gap now closes this campaign's attempts for that unavailable account. Its original X checkpoint still remains pending, and its collection result still reports partial coverage. No record claims a successful search. A later campaign can retry the source. The audit appears in `data/federal_collection_x_source_gaps.json`.

Cumulative model spending reached $41.878669, leaving $58.121331. Collection accounts for $4.457074 of that amount. Separate X spending reached $0.445.

## Reviewed source repairs and institutional source reuse

The assistant recovered 20 exact quotations from cached extraction proposals. Eighteen originally failed an exact office-title match. Personal attribution preserves their verified speakers without asserting that exact title. Two more use the existing supported single-author fields on Federal Reserve and SEC speech pages. Their quotations and dates remain unchanged. All 20 pass the unchanged validators on retained and freshly retrieved official sources. Independent source review also passed. The audit appears in `data/federal_collection_attribution_review.json`. Their required model judgments and Astra reviews run after this repair.

Joshua Rudd's January 29, 2026 nomination hearing uses the label `Lt. General Rudd.`. The parser now supports that exact prefix within its existing four-space paragraph rule. The reviewed mapping binds that label to the exact source and hearing day. It does not establish that Rudd held the NSA directorship before his appointment. Other speakers, inline mentions, unsupported indentation and written answers remain excluded.

The institutional profiles supplied 188 official URLs outside the archive inventory. Free source checks found 59 candidate pages, 101 pages without both a current official's name and AI content, and 28 retrieval gaps. These are leads for new personal attribution, not transferred institutional opinions. The archive's new `include_institution_sources` option also feeds these shared leads into daily collection. Every accepted personal statement still needs the existing source checks.

The collector now starts the next queued document when a worker finishes. Previously, each fixed group waited for its slowest document. The worker ceiling, extraction semaphore, shared budget manager, chunk limit and evidence lock remain unchanged. Budget or provider errors stop new submissions while existing work saves its results.

## Source attribution audit and corrections

Run 43242025047 completed collection and reviews and saved `d79afd18`. Its mechanical source replay counted 772 additions from 268 sources. A fresh manual check then found that a White House fact sheet narrated the President's actions instead of quoting his own words. The assistant expanded the audit to 35 new local-attribution records and obtained an independent source review.

The audit withdrew 21 original records and appended one clean replacement quotation. Eighteen records failed personal attribution: eight White House narratives, six FTC transcript turns with conflicting speaker labels, one answer assigned to the questioner in meeting minutes, one archive heading, one meeting readout, and one biography. Two more lacked sufficient author or full-source proof. One quotation included the reporter's attribution between the speaker's sentences; its replacement retains only a contiguous direct quotation. The other 14 audited records passed the context checks.

The records retain their original text, dates, source URLs, attribution and hashes. Withdrawn records now have `verified: false` and a documented reason. The correction audit lives in `data/federal_collection_attribution_corrections.json`. The fresh-source sample records its failed context check in `data/federal_collection_followup_spotcheck.json`. Exact text matches alone do not prove that the named official spoke the words. These targeted assistant checks do not establish a population accuracy rate.

The corrected campaign has 752 active additions from 260 sources. All pass the stricter offline source replay. Cumulative model cost remains $49.589249, with $50.410751 left. Separate X cost remains $0.445. The next run refreshes every corrected profile, including profiles whose last new statement was withdrawn.

The verifier now requires a directly retrieved source snapshot. Search text remains a lead and cannot become verified evidence. The archive collector avoids paid extraction for these unsupported snapshots. Personal local attribution also requires context beyond the quotation itself. Reviewed transcript turns and explicit document authors retain their separate identity checks. The conflicting FTC transcript has a source-specific exclusion for automatic personal attribution to Chris Mufarrige.

When a profile loses its last verified statement, the review runner preserves its previous Astra review in `retired_reviews` and removes it from the active review targets. It refreshes the empty profile without paying for an impossible summary with source citations. A lack of evidence does not become a neutral stance.

## Further sources and focused searches within the same allowance

Free checks covered 1,918 presidential archive documents from 2025 and 2026. Of these, 285 contain AI terms and the current President's administration heading. Conservative title and speaker checks selected 66 source leads. Independent review removed seven additional documents with other speakers. The existing quote, date and author checks still decide which excerpts qualify.

Free checks also covered 39 indexes and 97 documents in the military research and engineering archive. Eight documents contain both AI terms and a current official's name in the article body. Two news indexes now feed daily discovery. The combined archive extension adds 72 URLs outside the existing inventory.

The remaining search plan adds 33 queries for 63 low-evidence officials missing from the original query plan. It also adds 230 distinct, focused queries for 210 officials with one to fourteen verified excerpts. These queries cover AI safety and oversight, then deployment, public services, jobs, China and export controls. Completed queries and source extractions retain their caches. The selection details appear in `data/federal_collection_final_extension.json`.

The work bounds now allow 4,200 archive document checks and 413 saved queries. The original financial baselines and limits remain unchanged: $100 total model cost, $20 for collection within that total, at least $20 reserved before further collection, and the separate $5 X ceiling. The runner checks available provider credit again before execution.

## Fifth-wave review and specialist reporting archives

Run `43248872593` completed all 413 saved queries, ordinary analysis, named-policy work and Astra reviews. It added 13 excerpts. Independent review of all 13 found one false attribution: Senator Jeff Merkley narrated an imagined Trump reply about AI chips. The original `exec_trump/s125` record now remains on disk as unverified. The other 12 passed source/context review, and fresh retrieval reached all six source URLs. The audit lives in `data/federal_collection_fifth_source_review.json`. The corrected campaign has 764 active additions. Cumulative model cost reached $56.417549, leaving $43.582451. Separate X cost reached $0.46.

The presidential-document author check now requires a matching GovInfo DCPD package path and the President’s own name in the administration heading. A guest named in that heading cannot inherit the President’s statements. The regression test rejects mismatched domains, package IDs and guest names. This author check does not replace the separate review of speaker turns.

Free discovery checked 18 specialist-news sitemaps and 2,195 article pages. It found 436 new candidate pages naming 99 current officials. Of these, 159 name officials with fewer than 15 excerpts. These remain source leads until extraction and verification pass. The report lives in `data/federal_collection_news_extension.json`.

Four explicit reporting indexes now feed daily discovery: FedScoop, DefenseScoop, CyberScoop and GovCIO Media & Research. An index must opt in with `source_type: reported_statement`; its domain bounds still apply. Government-source defaults remain unchanged. The existing global 25-word quotation cap applies across federal profiles for each reporting source. The extractor now requests short, self-contained direct quotations for those sources, while retaining full source context for review. It must omit an excerpt if a shorter passage would change its meaning. Official-source prompts and unchanged official extraction caches remain unchanged. Ordinary judgments and Astra retain their existing criteria.

This extension keeps the same $100 cumulative model allowance, $20 collection allowance, $20 review reserve and separate X ceiling. It preserves all saved spending baselines and completed queries.

Four additional nomination hearings now have independently reviewed speaker mappings for Laura Swett, John Ratcliffe, Marco Rubio and Arvind Raman. Each mapping binds the full identity, exact oral speaker label, source URL and hearing date. Personal attribution avoids assigning a later office to the historical statement. The source review contains the exact identity proof.

## Sixth-wave results and review corrections

Run `43264626539` saved `b73e8e07`. It added 31 excerpts and completed ordinary analysis and named-policy judgments. Two independent Astra requests ended with `RemoteProtocolError`; Rubio and Ferguson remain pending for retry. Cumulative model cost reached $66.353103, leaving $33.646897. Collection accounts for $8.031677. Separate X cost remains $0.46.

Independent review checked all 31 additions across 20 exact retained sources. Fresh retrieval reached all 20 sources. Six short news excerpts lacked a clear subject, antecedent or substantive AI claim, so they now remain unverified. Three required replacements restore essential meaning. An additional Ferguson replacement supplies the preceding sentence about AI safety officials. Michael and Pugh use month precision because their sources establish a weekday or week, rather than an exact statement day. The review and fresh-source reports retain these outcomes explicitly.

A separate review checked 155 earlier additions across 60 sources. It found four Kratsios excerpts dated to the publication day rather than the stated delivery day. Their corrected date is October 8, 2026; correction metadata preserves the original date and anchor. Four incomplete excerpts now remain unverified. Complete replacements preserve Raman's and Holyoak's meaning. Existing complete excerpts already cover the Ferguson and Williams fragments. All original records remain available for audit.

Two cached news proposals now pass independent source review as personal statements: Hegseth's complete sentence about operational AI adoption and Kratsios's complete claim about the AI race. These recoveries retain the existing 25-word source limit. After all repairs and recoveries, the campaign has 789 active additions. Required judgments will refresh before completion.

The campaign replay originally tried to validate a public context placeholder for news excerpts. Public evidence deliberately omits copied attribution context. The corrected verifier recovers the exact private span using the retained source-text hash, start/end offsets, and span hash. It then runs the unchanged quote, speaker, date and role checks. Legacy rows can recover their original span from their source-specific extraction cache; active reporting rows now have immutable offsets. Prompt or model changes cannot discard that proof. Tests reject changed source snapshots, altered hashes, invalid offsets and unrelated extraction records. The 378-test suite and independent code review pass.

Free checks followed links from 436 news articles to 606 new primary-source URLs. Of these, 143 pages contain AI terms and a current official's name. Removing marketing parameters revealed three existing URLs, leaving 140 new source leads. A name in navigation, a signature list or a shared report does not prove personal authorship. These candidates still need the full verification process. The saved archive inventory also makes them available to daily collection. This extension retains all original financial limits and spending baselines.
