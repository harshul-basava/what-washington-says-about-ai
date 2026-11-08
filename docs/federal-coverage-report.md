# Federal coverage audit — 2026-11-08

The registry contains 150 people and 36 institutions across 41 organizations. Each profile completed eight separate historical search passes. The source pass also checked government pages and testimony. The collection contains 1,522 excerpts from 687 distinct source pages.

This completes the planned web research effort. Evidence depth remains below Congress. Missing evidence does not establish a neutral or opposing stance.

## Comparison of people

Institution excerpts do not enter this comparison. Quote counts measure available evidence, not search completeness or importance.

| Metric | Federal people | Congress |
|---|---:|---:|
| Profiles | 150 | 649 |
| Stored excerpts | 1033 | 15728 |
| Median excerpts per person | 5 | 12 |
| Median source pages per person | 4 | 10 |
| Median quoted words per person | 125.5 | 584 |

## Coverage by daily group

| Group | People | Institutions | Median excerpts per person | People without excerpts |
|---|---:|---:|---:|---:|
| White House and executive policy offices | 50 | 9 | 4 | 4 |
| Commerce and its agencies | 25 | 7 | 4 | 5 |
| NSA and its security center | 6 | 2 | 8 | 0 |
| Intelligence community | 8 | 2 | 5 | 1 |
| Defense and military AI | 10 | 2 | 8.5 | 0 |
| Treasury | 6 | 1 | 5.5 | 0 |
| State and trade policy | 10 | 3 | 5 | 0 |
| Justice and its task forces | 7 | 3 | 3 | 0 |
| Homeland security and CISA | 7 | 2 | 4 | 0 |
| Energy | 4 | 1 | 11.5 | 0 |
| Procurement and personnel | 8 | 2 | 7.5 | 1 |
| Federal Trade Commission | 5 | 1 | 24 | 0 |
| Health and social security | 2 | 0 | 4.5 | 0 |
| Environmental Protection Agency | 1 | 0 | 7 | 0 |
| White House Super Intelligence Force | 1 | 1 | 6 | 0 |

## Remaining evidence gaps

The following profiles have no verified excerpts after the historical searches:

- Richard Walters.
- Thomas Flagg.
- Thomas Lind.
- Jake Easter.
- Noah Jaffe.
- John Sonderman.
- Katherine Reid.
- Jessica Curyto.
- Ted Suzman.
- Allison Curran.
- Jennifer Hill.

The government source pass retains 18 distinct pages for retry. These pages include unavailable sources and incomplete model output. Per-profile counts and source errors remain in `data/federal_seed_research.json`.

Federal research lacks the API-backed X archive and bulk govinfo collection used for Congress. It includes indexed public posts and publicly available testimony. Some new or operational officials have few public AI statements. Dates remain unknown when the source does not establish them. Roles and memberships require manual review.

## Daily inclusion

All 186 profiles have named queries in 15 source groups. The configuration produces 111 queries and checks up to six queued pages per group per invocation. Searches run with up to four workers. The daily schedule remains 11:00 UTC and activates this code after merge into the default branch.

The live collection on 2026-11-08 has status `partial` with 377 queued pages. Policy assessment has 0 pending model pairs. Human-review cases remain separate from pending model work.

The existing monthly and lifetime caps remain unchanged. Budget limits and source failures preserve checkpoints for later runs. The site reports these limits and offers `site/data/federal_coverage.csv` for every profile.
