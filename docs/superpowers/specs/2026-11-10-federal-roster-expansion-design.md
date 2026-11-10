# Federal leadership and office coverage

Date: 2026-11-10

Status: Implementation in progress. The five-person pilot is complete. On November 10, the user limited the active roster to 500 current federal people total. Institutions remain separate. Discovered roles outside that selection remain in the inventory. The authorized OpenRouter lifetime cap is now $500 and the federal daily model allowance is $4, superseding the older values retained below.

## Intent

Cover influential current government officials across every executive department, the White House, federal agencies, and their offices. The user explicitly includes CISA, CIA, NSA, Commerce, and the superintelligence task forces. The current 62 officials are a verified subset of an incomplete candidate list. They are not a coverage target.

The result should answer two separate questions: who holds relevant government power, and what public evidence establishes their views on AI? A person can qualify for the roster without an AI statement, score, or X account.

The user previously limited coverage to current government officials and government institutions. Former officials, private commentators, informal advisers, and contractors remain outside the active roster. Historical statements from an eligible current official remain useful when their dates and capacity are clear.

## Definition of influence

Use documented authority and responsibilities, not social-media popularity or frequency of AI statements. Review every office in the agency inventory. Include all publicly identified current incumbents who satisfy either rule below.

1. **Senior leadership:** Department and agency heads, principal deputies, chiefs of staff, undersecretaries, assistant secretaries, bureau heads, office heads with substantive policy authority, commissioners, and their equivalents. Include inspectors general where they oversee these agencies. These officials qualify through their authority, even without explicit AI responsibilities.
2. **Specific decision authority:** Officials below those levels who direct AI policy, research, evaluation, safety, security, infrastructure, procurement, budgets, deployment, export controls, standards, competition, or enforcement. Include relevant deputies, program directors, and senior policy staff when a source identifies their responsibility. Include civil servants and acting officials on the same basis as political appointees.

Document the qualifying role and authority for each person. A nominal title alone does not establish decision authority below senior leadership. An assistant, outside board member, fellow, or event participant does not qualify automatically. Formal advisers qualify only when evidence establishes current government service. Do not infer employment from access to officials.

These rules define an auditable scope for "all influential people." Public sources cannot establish a complete census of undisclosed intelligence staff or informal influence.

## Coverage universe

Start with the federal agency directory, then inspect each agency's organization chart, leadership directory, component directories, and appointment notices. Verify current names and structures at execution time. Keep stable repository IDs when an office changes its display name.

| Area | Required inventory |
|---|---|
| White House and Executive Office of the President | President, Vice President, chief of staff and relevant deputies; senior assistants and advisers; science and technology, management and budget, national security, economic policy, domestic policy, trade, cyber, and other substantive policy offices. Review the Super Intelligence Force and related councils separately. |
| All 15 executive departments | Agriculture, Commerce, defense/war, Education, Energy, Health and Human Services, Homeland Security, Housing and Urban Development, Interior, Justice, Labor, State, Transportation, Treasury, and Veterans Affairs. Inventory department leadership and component offices. |
| Intelligence and cyber | CIA, NSA, CISA, the Office of the Director of National Intelligence, and every publicly listed intelligence-community component. Include relevant cyber commands and intelligence research, acquisition, technology, and security offices. Count overlapping department memberships once. |
| Commerce detail | Export administration and enforcement, standards, AI evaluation and safety, telecommunications, technology policy, intellectual property, and relevant semiconductor programs. Check bureau and program leadership beyond the department's main leadership page. |
| Independent agencies and regulators | Review every executive or independent agency in the directory for senior leadership and substantive offices. Explicitly check the Federal Trade Commission, Federal Communications Commission, Securities and Exchange Commission, financial regulators, Federal Reserve, energy and nuclear regulators, National Science Foundation, NASA, General Services Administration, Office of Personnel Management, and Social Security Administration. |
| Cross-agency offices and task forces | Review active AI, superintelligence, procurement, research, enforcement, and security bodies. Record the formal membership evidence for each official. Keep White House and Justice Department task forces separate. |

This is a discovery universe, not a claim that every named office currently exists or that its incumbent is known. Record reorganizations, abolished offices, vacancies, and offices with no public incumbent. Congress and the judiciary remain outside this expansion. Legislative agencies do not enter the executive roster.

## Inventory and eligibility

Create `config/federal_roster_inventory.json` as a review record. It complements the existing eligibility gate; it never enables a profile by itself. Include all existing eligible officials in the review.

The inventory contains organization discovery records and role records. A discovery record stores an organization key, optional registry organization ID, parent key, official directory URLs, review date, and `pending` or `reviewed` status. A reviewed organization lists its reviewed component directories and the role IDs found there. An empty discovery result needs a reason.

A role record stores a stable role ID, organization key, title, authority class, authority reason, source URLs, check date, current-service evidence, candidate name, optional subject ID, and one of these states: `included`, `candidate`, `unresolved`, `vacant`, `not_public`, or `out_of_scope`. `included` requires a matching person who passes `config/federal_scope.json`. Only included people reach collectors and public profiles. Sources must support current service, rather than merely an old appointment.

One person can fill several role records but has one subject ID and one primary organization. Role coverage and person counts remain separate. A missing biography or failed request creates a review issue; it does not prove departure. Recheck roles before each release. A weekly directory review creates proposed changes for review; it never automatically promotes a candidate or removes an official after a page failure.

## Research and judgments

Publish verified roster additions with accurate research status, including empty profiles. Then complete historical research for each new official using the existing eight-pass method. Use official biographies, speeches, testimony, hearings, press releases, policy documents, interviews, podcasts, and verified X accounts. Read full sources where available. Search for contrary views and changes over time. Search discovery can extend before 2023 when a relevant older statement appears; reconstructed monthly charts retain their existing 2023 start.

Verify excerpts, dates, speaker identity, and attribution. Preserve stable statement IDs. An agency release does not establish its leader's personal opinion. An older statement does not establish a current institutional position. Record inaccessible sources and search limits explicitly.

Use the official X API with sourced account ownership, numeric author checks, and ownership dates. A missing account does not block web research or roster inclusion. For each cohort, freeze an archive cutoff, preserve existing checkpoints, and record partial pagination. Verified handles enter daily updates; unverified handles remain leads.

Reuse the congressional five questions, 23 regulation categories, summaries, topics, histories, and named-policy rubrics. Keep the existing DeepSeek/Sol/Astra strategies and confidence thresholds. Complete a final Astra review of the overall AI stance for every new profile with verified evidence. Use a separate expansion audit, retrieve requested context, and preserve explicit no-stance results. No-evidence profiles require no model calls. Do not force a score to improve coverage.

## Daily operation and public presentation

Every new eligible profile needs a named web query, agency-source routing, and a place in the judgment queue. Every verified active X account needs daily collection. Extend agency domains and groups with the roster. Retain oldest-first scheduling and resumable work under the existing caps.

Report scheduled profiles, completed searches, pending judgments, last successful collection, and the oldest pending work. A daily workflow does not imply that every query finishes each day. Measure pilot throughput before promising that frequency.

Keep the current Congress-style charts. Add office navigation and role information to federal profiles. Department totals count unique people; office filters include linked roles. Institutions retain their own view. Agency coverage shows discovery status, included people, unresolved candidates, vacant roles, and evidence/judgment completion. Do not label a fraction as the share of all employees or all influential officials.

## Delivery and resource limits

First finish the organization inventory and publish an agency-by-agency gap report. Then run a five-person pilot across different agency and evidence types. Use subsequent cohorts of 10–20 people as an operational default. These are batch sizes, not a cap on the roster. Finish original priority groups first, then all remaining departments, agencies, and component offices. Continue until every discovered office and qualifying role has a documented disposition.

Keep the existing lifetime caps: OpenRouter $350, X $150, and Exa $100. Keep monthly daily-job caps: OpenRouter $35, X $40, and Exa $10. Keep X batches at $2 and the federal daily judgment allowance at $2. Refresh ledger state before paid execution and include all research, context, and review costs. Connected search charges may not appear in the repository ledger.

The first pilot has an aggregate ceiling of $12 for OpenRouter, $4 for X across two $2 batches, and $2 for metered search. These are proposed execution limits within existing caps. Stop with pending work if a ceiling prevents completion. Estimate the remaining cost from the pilot; seek a budget change only if completion requires it. Do not claim that the current budget can fund the entire expanded roster.

## Acceptance

The inventory covers every department and discovered agency, component, and substantive office. Every qualifying public incumbent has an included profile or a sourced unresolved/exclusion reason. No row remains silently unreviewed. Publication preserves current-service checks, statement attribution, histories, separate denominators, and Congressional data.

Report roster completion, historical-search completion, judgment completion, and daily freshness separately. A budget-limited backfill can coexist with a complete roster inventory; it cannot count as complete research. The final report lists residual gaps, sources, costs, and dates.

## Sources and builder decisions

Discovery starts from the [USA.gov agency directory](https://www.usa.gov/agency-index), [Executive Office directory](https://www.whitehouse.gov/eop/), and [Director of National Intelligence directory](https://www.odni.gov/about/). These pages supply starting points; their top-level lists do not establish complete office coverage. The CISA leadership page returned a 403 during planning, so execution must try other official pages or record that access gap.

Builder decisions in this proposal: role-based inclusion rules, the inventory format, five-person pilot, 10–20-person cohorts, final Astra review, and weekly role checks. The user requested broad current-government coverage, historical research, shared analysis, and daily updates. They did not set a target headcount.
