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

Discovery produced 1,084 role records before the final identity and authority review. A role record describes a position and its named holder, with a source and check date. Several roles can belong to one person. These records do not establish 1,084 eligible people.

The selected roster will prioritize documented senior authority and responsibility for AI, security, export controls, research, procurement, and regulation. The review preserves all departments and the specified White House, intelligence, cyber, and independent-agency coverage. Source gaps and candidates outside the selected 500 will remain in the office inventory. They will not enter collection or public profile counts.

The larger roster, historical backfills, and final Astra reviews remain in progress. Pilot completion does not establish completion of that work. Source access failures, uncertain current roles, and missing account ownership remain explicit limits.

## Daily update implementation

The daily job alternates priority between broad analysis and named-policy judgments under one $4 allowance. Each pipeline rotates through profiles and statement batches. Bounded rounds prevent recurring evidence and invalid outputs from blocking older work. A zero remaining allowance preserves explicit backlog counts.

The existing daily workflow also checks a bounded set of government directories each week. A changed page creates a review item. It does not automatically change eligibility. The public coverage table separates office discovery, current officials, unresolved roles, and vacancies.
