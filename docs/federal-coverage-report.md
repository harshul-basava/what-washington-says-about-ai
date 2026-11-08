# Federal coverage audit — 2026-11-08

The registry contains 150 people and 36 institutions across 41 organizations. Each profile completed eight separate historical web search passes. A separate source pass checked government pages and testimony. The combined corpus contains 2,686 excerpts from 1,809 distinct source URLs, including 1,114 direct X excerpts.

Evidence depth remains below Congress. Missing evidence does not establish a neutral or opposing stance.

## Comparison of people

Institution excerpts do not enter this comparison. Quote counts measure available evidence, not search completeness or importance.

| Metric | Federal people | Congress |
|---|---:|---:|
| Profiles | 150 | 649 |
| Stored excerpts | 1133 | 15728 |
| Median excerpts per person | 5 | 12 |
| Median source URLs per person | 4 | 10 |
| Median quoted words per person | 130.5 | 584 |

## Coverage by daily group

| Group | People | Institutions | Median excerpts per person | People without excerpts |
|---|---:|---:|---:|---:|
| White House and executive policy offices | 50 | 9 | 4 | 4 |
| Commerce and its agencies | 25 | 7 | 4 | 5 |
| NSA and its security center | 6 | 2 | 8 | 0 |
| Intelligence community | 8 | 2 | 5 | 1 |
| Defense and military AI | 10 | 2 | 8.5 | 0 |
| Treasury | 6 | 1 | 6.5 | 0 |
| State and trade policy | 10 | 3 | 5 | 0 |
| Justice and its task forces | 7 | 3 | 3 | 0 |
| Homeland security and CISA | 7 | 2 | 4 | 0 |
| Energy | 4 | 1 | 11.5 | 0 |
| Procurement and personnel | 8 | 2 | 7.5 | 1 |
| Federal Trade Commission | 5 | 1 | 24 | 0 |
| Health and social security | 2 | 0 | 4.5 | 0 |
| Environmental Protection Agency | 1 | 0 | 7 | 0 |
| White House Super Intelligence Force | 1 | 1 | 6 | 0 |

## Historical X search

The November 8 backfill imported 1,114 excerpts from 23 sourced accounts for 21 profiles. The collector processed 152 successful pages. X supplied completion signals for 18 account intervals; 5 intervals remain pending.

The pending accounts returned three consecutive pages without new post IDs or an end marker. Their cursors remain available for a later retry. This limit does not establish a complete archive. The following accounts need another attempt:

- @BISgov (Bureau of Industry and Security (BIS)).
- @cia (Central Intelligence Agency).
- @USTreasury (Department of the Treasury).
- @FTC (Federal Trade Commission).
- @VP46archive (Kamala Harris).

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

The government source pass retains 18 distinct pages for retry. These include unavailable sources and incomplete model output. Per-profile counts and errors remain in `data/federal_seed_research.json`. Roles and memberships require manual review.

## Daily inclusion

All 186 profiles have named queries in 15 source groups. The configuration produces 111 queries and checks up to six queued pages per group per invocation. Searches run with up to four workers. The daily schedule is 11:00 UTC. Fork workflows default to federal-only updates and accept explicit source overrides.

The latest federal web report retains 321 queued pages. The current policy corpus has 490 candidate excerpts and 592 statement-policy pairs. Model assessment has 0 pending pairs; 10 pairs require human review and remain outside accepted stance charts.

The existing monthly and lifetime caps remain unchanged. Budget limits and source failures preserve checkpoints. The site reports coverage and provides `site/data/federal_coverage.csv` for every profile.

The first [live fork workflow](https://github.com/kaustubhkislay/what-washington-says-about-ai/actions/runs/42525797611) added 50 web excerpts and completed 16 new policy assessments, including two Astra reviews. It processed 30 X search pages without authentication or source errors. These pages added no posts beyond the historical import. Fifteen daily X windows retain pending cursors after the page limit. The workflow reports failure because collection remains partial, but its report and commit/push steps succeeded. Bot commit `57265fb` saved the results. The run cost $0.4509.
