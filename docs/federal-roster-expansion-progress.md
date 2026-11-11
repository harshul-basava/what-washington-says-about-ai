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

The first expansion cohort completed all 160 historical web passes for 20 officials. Full-source checks brought this cohort to 68 verified web excerpts. Two source URLs still need a retry. This stage cost $5.840603 through OpenRouter. The cohort's judgments and final Astra review remain pending. The remaining 413 additions still need historical web research. The five-person pilot is the only completed expansion cohort.

The repository permits another $185.546279 of OpenRouter spending under its unchanged lifetime cap. A [read-only check of the original repository secret](https://github.com/harshul-basava/what-washington-says-about-ai/actions/runs/42947939389) found $162.11 in account credit. However, its $200 OpenRouter workspace cap leaves only $8.32 usable, with no scheduled reset. Later bulk research and model reviews await a workspace allowance change. The check made no paid model calls and changed no limits. The site distinguishes research that has not started, completed searches with no verified excerpts, and pending judgments.

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
