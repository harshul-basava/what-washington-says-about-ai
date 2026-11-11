# Federal roster expansion: execution record

Updated November 11, 2026.

The user set a limit of 500 current federal officials on November 10. This total includes the existing roster and the five pilot additions. Government institutions have a separate count. The expansion does not change the congressional roster.

## Completed pilot

| Official | Current office | Verified web excerpts | Verified X excerpts |
| --- | --- | ---: | ---: |
| Stephen Miller | White House chief of staff | 1 | 4 |
| S. Shyam Sunder | NIST laboratory programs | 0 | 0 |
| Michael Ellis | CIA deputy director | 8 | 2 |
| Paul S. Atkins | SEC chairman | 8 | 4 |
| Brian Brotsos | Transportation data and superintelligence office | 1 | 0 |

Each official received eight historical web passes. The source follow-up read available government pages in full. Forty completed passes produced 18 verified web excerpts. The official X API added ten excerpts from three sourced accounts. Its archive cutoff was November 10, 2026, exclusive. No verified account mapping was available for Sunder or Brotsos.

All 28 excerpts completed the five-question analysis. The four evidence-bearing profiles completed regulation analysis, summaries, topics, histories, and an independent Astra review of overall AI stance. Named-policy judgments also completed. Astra requested wider context for one web excerpt and two X posts. The final review used all three retrieved sources. Astra found no qualifying overall AI stance in this pilot's evidence; narrower judgments remain available. Sunder's empty profile remains visible and unscored.

| Pilot cost | Recorded USD |
| --- | ---: |
| Web research, extraction, all model judgments, and Astra reviews | 1.856556 |
| Official X collection and requested post context | 0.09 |
| Total recorded cost | 1.946556 |

The OpenRouter lifetime cap remains $500. The project ledger had $191.386882 left after this pilot. The X lifetime cap remains $150, and its monthly daily-update cap remains $40. No budget increase accompanied the reduced roster scope. Connected discovery tools may have separate billing outside this ledger.

The [expansion manifest](../data/federal_roster_expansion.json) records the pilot IDs, costs, stages, and new scope. The [Astra audit](../data/federal_roster_expansion_review_pilot.json) preserves its findings and context requests. The original repository ran [historical X collection](https://github.com/harshul-basava/what-washington-says-about-ai/actions/runs/42914054813) and [requested X context](https://github.com/harshul-basava/what-washington-says-about-ai/actions/runs/42915367102).

## Roster selection and remaining work

Discovery produced 1,089 role records, including five supplemental department principals, before the final identity and authority review. A role record describes a position and its named holder, with a source and check date. Several roles can belong to one person. These records do not establish 1,089 eligible people.

The selected roster contains 500 current people and 35 separate institutions. It adds 433 people to the 67 officials present after the pilot. Selection prioritizes documented senior authority and responsibility for AI, security, export controls, research, procurement, and regulation. The review preserves all departments and the specified White House, intelligence, cyber, and independent-agency coverage. Source gaps and candidates outside the selected 500 remain in the office inventory. They do not enter collection or public profile counts. Later eligibility corrections preserve the initial selection in dated amendments.

The first expansion cohort completed all 160 historical web passes for 20 officials. After the attribution repair, all 133 web and X excerpts completed broad and named-policy analysis. Astra reviewed all 16 profiles with evidence and accepted five overall-AI findings. The initial resumed run cost $1.432976; the repair review cost $0.474381. One FERC directory remained inaccessible for two profiles.

An independent source check then found three attribution failures. The validator rejected Powell's transcript speaker label and two officials' speech headers. A reviewed mapping now binds Powell's speaker label to six official transcripts, exact dates, and uninterrupted speaker turns. The speech fix requires exact authorship headers. Offline revalidation recovered 22 Powell excerpts, two Hurley excerpts, and one Paoletta excerpt. Three nonmatching Powell candidates remain rejected. All 25 recovered excerpts completed judgments and renewed Astra review. The [revalidation audit](../data/federal_cached_reverification.json) records the recovery and zero paid calls.

The second 20-person cohort completed 160 historical web passes and initially added 113 verified excerpts. Its retry added six more excerpts. All 204 web and X excerpts completed broad and named-policy analysis. Astra reviewed all 19 profiles with evidence, including the requested X context, and accepted 13 overall-AI findings. The first run cost $8.676535; the retry cost $0.293669. The same FERC directory remains inaccessible for two profiles in the latest attempt. Later groups retain their own stage records in the backfill status.

The first two resumed cohorts and their repairs cost $10.877561 in total. The batch launcher has a $150 total model allowance, including retries, measured from ledger spending of $314.4537210994765. It stops on incomplete work and preserves the remaining allowance across restarts. The [backfill status](../data/federal_backfill_status.json) records each stage and cost.

The third 20-person cohort completed all 160 historical passes and added 61 excerpts. All 143 web and X excerpts completed broad and named-policy analysis. Astra reviewed 16 profiles and accepted nine overall-AI findings. This cohort cost $8.281588. It finished in about 16 minutes under the previous worker limits. At this checkpoint, the resumed work cost $19.159149, leaving $130.840851 of the same $150 allowance. Historical web research remains pending for 373 additions.

The fourth cohort completed its 160 historical passes and judgments for 110 excerpts. Astra reviewed 15 profiles and accepted five overall-AI findings. Repairs fixed a concurrent ledger-read failure and reused verified source context for excerpts from the same page. The context repair requires the exact source URL, hash, and both original excerpts. It does not relax quote or attribution checks. The saved total after this cohort was $27.460639, leaving $122.539361 of the same $150 allowance. This total includes failed requests, retries, and a diagnostic review. A request with uncertain billing retains its conservative reservation.

A separate official-source audit recovered 17 missed excerpts for Aaron Lukas, Bradley Hansell, Kenneth Wilsbach, and Jared Isaacman. Each written answer passed manual checks against its exact question boundaries and source hash. The audit preserves unknown answer dates and identifies Hansell's exact document dateline. It does not treat the questions as the nominee's statements. A narrow authored-message header correction also supports Isaacman's NASA letter. The [manual source audit](../data/federal_manual_source_review.json) records these excerpts and zero paid calls. All 17 additions completed renewed judgments and Astra review for $0.398177.

A follow-up audit recovered 24 more answer excerpts: nine for Christopher Mahoney, six for Dan Caine, four for Arielle Roth, and five for Kenneth Wilsbach. The [follow-up audit](../data/federal_manual_source_followup.json) records exact answer boundaries and source hashes. Caine's official biographical questionnaire explicitly connects Dan Caine and John Daniel Caine; the registry now retains that sourced full-name alias. Roth's one-word answer remains a documented limitation because it falls below the excerpt-length requirement. The questions never become part of an official's quotation. These 24 additions await renewed judgments and Astra review.

The [source-access follow-up](../data/federal_source_access_followup.json) found Labor's replacement HTTPS inventory URL and updated the future research seed. Its departmental descriptions do not establish personal views. HHS's leadership page returned a client-rendered shell. The FERC directory was accessible locally and contained roles without AI statements. Historical workflow gaps remain unchanged in their audit records. This follow-up made no paid calls and added no personal excerpts.

The fifth cohort completed all requested stages, including judgments for 120 excerpts and Astra review of 12 profiles. Astra accepted one overall-AI finding. The run cost $6.991686. The saved sequence total reached $34.452325, leaving $115.547675 before the source-repair reviews and remaining cohorts. The original cumulative allowance remains $150.

At resumption, the repository permitted another $185.546279 of OpenRouter spending under its unchanged lifetime cap. The user authorized a $350 workspace cap. The [read-only check before resumption](https://github.com/harshul-basava/what-washington-says-about-ai/actions/runs/42954239646) confirmed that cap, $162.11 in account credit, and $158.32 usable. These balances precede the resumed research costs. The check made no paid model calls.

The manual backfill workflow uses the original repository secret inside GitHub Actions. Each run shares an allowance of at most $25 across research, extraction, analysis, and Astra review. All runs also obey the provider and repository limits. The workflow saves evidence, judgments, costs, and resumable source checkpoints after each attempt. Source access failures remain explicit. Incomplete model responses remain pending.

The accelerated backfill allows up to 20 workers for research, extraction, broad analysis, and final Astra reviews. Each person's eight research passes remain sequential and retain their original prompts, source checks, and model settings. One workflow writes results at a time. Named-policy analysis and source-context retrieval retain four workers. All model requests reserve their maximum estimated cost before dispatch. Workers wait when active requests temporarily occupy the allowance. Uncertain costs retain their reservations; only a reported valid cost or a confirmed rejection before dispatch releases a reservation. Web requests retain the 600-second timeout and use one transport attempt per reservation. Daily worker settings and all spending caps remain unchanged.

Public account searches covered all 433 additions. They found source-supported mappings for 45 people; four other leads need more account evidence. The bounded search found no verified account for 384 people. Across the new and retained people, this work adds 51 account intervals for 46 people. The search does not establish that the other people have no public account.

Three official X batches added 425 verified excerpts for $3.00 in recorded API cost. Collected posts passed the numeric author checks. All 14 required original-post author checks passed, including the later Selig mapping. The batches skipped model judgments. New excerpts remain available on the site with pending assessments. These bounded keyword searches do not establish complete X histories.

The API could not retrieve the personal accounts previously documented for Olivia Trusty and Michael S. Selig. The [account follow-up](../data/federal_roster_x_unavailable_followup.json) preserves those failures and sources. Separate sources identify their government-role accounts, `OliviaTrustyFCC` and `ChairmanSelig`. Collection uses these accounts from June 28, 2025 and January 21, 2026, respectively. The final batch verified both accounts and added 14 Trusty excerpts and 27 Selig excerpts. These mappings do not establish that the old accounts changed names. The older personal histories remain unavailable.

David Fotouhi and Keith Sonderling have current account mappings that begin November 10, 2026. Their intervals start at the archive cutoff, so they have no historical window in this batch. Their daily checks remain configured. The complete daily registry contains 113 account intervals for 99 profiles.

All 49 new account intervals before the cutoff completed the bounded archive search. The Miller interval also completed its repeat check after an ownership-date correction. The [expansion manifest](../data/federal_roster_expansion.json) links the three runs and records their separate costs. Historical completion does not fulfill a later daily check.

The account review also found a stale Treasury biography. A November 6 employer announcement confirms Jonathan McKernan returned to private practice. His replacement is Jennifer Murphy. Conflicting sources leave Michael J. Rigas’s current service unresolved; Jennifer Schoen fills that slot. Dated amendments preserve both original selection decisions. William K. Marshall III remains eligible after a fresh Bureau of Prisons biography check.

The larger roster, historical backfills, and final Astra reviews remain in progress. Pilot completion does not establish completion of that work. Source access failures, uncertain current roles, and missing account ownership remain explicit limits.

## Daily update implementation

The daily job alternates priority between broad analysis and named-policy judgments under one $4 allowance. Each pipeline rotates through profiles and statement batches. Bounded rounds prevent recurring evidence and invalid outputs from blocking older work. A zero remaining allowance preserves explicit backlog counts.

The existing daily workflow also checks a bounded set of government directories each week. A changed page creates a review item. It does not automatically change eligibility. The public coverage table separates office discovery, current officials, unresolved roles, and vacancies.
