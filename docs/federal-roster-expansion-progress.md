# Federal roster expansion: execution record

Updated November 10, 2026.

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

The first expansion cohort completed all 160 historical web passes for 20 officials. Its original 108 web and X excerpts completed the broad and named-policy analyses. Astra reviewed all 13 profiles with evidence and accepted four overall-AI findings. The resumed model work cost $1.432976. One FERC directory remained inaccessible for two profiles.

An independent source check then found three attribution failures. The validator rejected Powell's transcript speaker label and two officials' speech headers. A reviewed mapping now binds Powell's speaker label to six official transcripts, exact dates, and uninterrupted speaker turns. The speech fix requires exact authorship headers. Offline revalidation recovered 22 Powell excerpts, two Hurley excerpts, and one Paoletta excerpt. Three nonmatching Powell candidates remain rejected. These 25 additional excerpts still need judgments and renewed Astra review. The [revalidation audit](../data/federal_cached_reverification.json) records the work and zero paid calls.

The second 20-person cohort completed 160 historical web passes and added 113 verified excerpts. All 198 of its web and X excerpts completed broad and named-policy analysis. Astra retrieved additional X context and still needs to review the last returned context. This run cost $8.676535 in model calls. The same FERC directory remains inaccessible for three more profiles. Historical web research remains pending for 393 additions.

The resumed model runs have cost $10.109511 so far. The batch launcher has a $150 total model allowance, including retries. It stops on incomplete work and preserves the remaining allowance across restarts. The [backfill status](../data/federal_backfill_status.json) records each stage and cost. Later groups wait until the attribution fix and the incomplete Astra review finish.

The repository permits another $185.546279 of OpenRouter spending under its unchanged lifetime cap. The user authorized a $350 workspace cap. The [latest read-only check](https://github.com/harshul-basava/what-washington-says-about-ai/actions/runs/42954239646) confirms that cap, $162.11 in account credit, and $158.32 usable. The earlier update attempt lacked management access. The later check confirms the change. It made no paid model calls.

The manual backfill workflow uses the original repository secret inside GitHub Actions. Each run shares an allowance of at most $25 across research, extraction, analysis, and Astra review. All runs also obey the provider and repository limits. The workflow saves evidence, judgments, costs, and resumable source checkpoints after each attempt. Source access failures remain explicit. Incomplete model responses remain pending.

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
