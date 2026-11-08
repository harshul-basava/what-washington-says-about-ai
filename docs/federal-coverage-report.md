# Federal coverage audit — 2026-11-08

The registry contains 150 people and 36 institutions across 41 organizations. Each profile completed eight separate historical web search passes. A separate source pass checked government pages and testimony. The combined corpus contains 3,066 excerpts from 1,948 distinct source URLs, including 1,114 direct X excerpts.

Evidence depth remains below Congress. Missing evidence does not establish a neutral or opposing stance.

## Comparison of people

Institution excerpts do not enter this comparison. Quote counts measure available evidence, not search completeness or importance.

| Metric | Federal people | Congress |
|---|---:|---:|
| Profiles | 150 | 649 |
| Stored excerpts | 1343 | 15728 |
| Median excerpts per person | 6 | 12 |
| Median source URLs per person | 4 | 10 |
| Median quoted words per person | 164.5 | 584 |

## Coverage by daily group

| Group | People | Institutions | Median excerpts per person | People without excerpts |
|---|---:|---:|---:|---:|
| White House and executive policy offices | 50 | 9 | 4.5 | 4 |
| Commerce and its agencies | 25 | 7 | 5 | 5 |
| NSA and its security center | 6 | 2 | 8.5 | 0 |
| Intelligence community | 8 | 2 | 5.5 | 1 |
| Defense and military AI | 10 | 2 | 11.5 | 0 |
| Treasury | 6 | 1 | 7 | 0 |
| State and trade policy | 10 | 3 | 6 | 0 |
| Justice and its task forces | 7 | 3 | 3 | 0 |
| Homeland security and CISA | 7 | 2 | 7 | 0 |
| Energy | 4 | 1 | 15.5 | 0 |
| Procurement and personnel | 8 | 2 | 9.5 | 1 |
| Federal Trade Commission | 5 | 1 | 24 | 0 |
| Health and social security | 2 | 0 | 5 | 0 |
| Environmental Protection Agency | 1 | 0 | 8 | 0 |
| White House Super Intelligence Force | 1 | 1 | 6 | 0 |

## Historical X search

The November 8 emusks backfill imported 1,114 excerpts from 23 sourced accounts for 21 profiles. The collector processed 159 successful pages. Emusks supplied completion signals for 23 account intervals; 0 emusks intervals remain pending.

The follow-up completed the five remaining historical intervals and all daily windows. It found no additional posts. Provider completion signals do not establish a complete archive.

The configuration now selects the official X API. Its federal searches have not started. It uses separate checkpoints and retains existing evidence with its emusks provenance. The original repository's existing bearer secret passed a congressional API run; the original owner must merge the switch before daily federal collection can use it.

Another 165 profiles need sourced X account mappings. The [X coverage report](federal-x-coverage.md) lists mappings, ownership dates, and gaps. Bulk govinfo collection remains absent.

## Remaining evidence gaps

The following people have no verified excerpts after these searches:

- Allison Curran.
- Jake Easter.
- Jennifer Hill.
- Jessica Curyto.
- John Sonderman.
- Katherine Reid.
- Noah Jaffe.
- Richard Walters.
- Ted Suzman.
- Thomas Flagg.
- Thomas Lind.

The follow-up checked 339 source URLs, including all 321 queued daily pages and the 18 pending government sources. It added 380 verified excerpts. Exact-source checks rejected 590 distinct model proposals across extraction attempts, including proposals later repaired. Rejected proposals never enter evidence. The audit records resolved URLs, source hashes, and exclusions in `data/federal_web_completion.json`. This bounded source review does not establish exhaustive coverage. Roles and memberships require manual review.

## Daily inclusion

All 186 profiles have named queries in 15 source groups. The configuration produces 111 queries and checks up to six queued pages per group per invocation. Searches run with up to four workers. The daily schedule is 11:00 UTC. Fork workflows default to federal-only updates and accept explicit source overrides.

The latest federal web report retains 0 queued pages. The current policy corpus has 547 candidate excerpts and 663 statement-policy pairs. Model assessment has 0 pending pairs; 10 pairs require human review and remain outside accepted stance charts.

The existing monthly and lifetime caps remain unchanged. Budget limits and source failures preserve checkpoints. The site reports coverage and provides `site/data/federal_coverage.csv` for every profile.
