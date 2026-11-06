<!-- rubric v3 (DRAFT, not yet used for scoring) -->
# Scoring rubric (v3 draft)

## The idea

Every question is a **claim**. A member's score is how strongly *they* back that claim in their own words, on one five-step scale with the same shape for every question:

| Score | Shape | Meaning |
|---|---|---|
| 0 | strongly disagree / absent | rejects the claim, or never engages with it |
| 1 | disagree / weak | engages, but downplays or hedges |
| 2 | neutral / moderate | backs the claim as a real consideration |
| 3 | agree | backs it strongly enough to want action on it |
| 4 | strongly agree | treats it as central or a top priority |

Scoring happens in two steps, so the result can be traced and checked:

1. **Label each statement (model).** For every statement, the model decides whether it speaks to each question *in the member's own voice*. If it does, the model gives it the single level whose **test** it meets. Otherwise it gets no label. The labels are saved and shown next to each quote.
2. **Turn labels into a score (fixed code, no model).** The rules are in "Aggregation" below. Anyone can recompute a score from the labels.

## Rules for labeling a statement (all questions)

- **Own voice only.** Reporting someone else's view ("AI CEOs warn…", "experts predict…") gets no label unless the member clearly adopts it, for example by saying they share the concern or by calling for action because of it.
- **One level per statement per question:** the highest level whose test the statement fully meets.
- **No label** if the statement doesn't address the question. Most statements touch only one or two questions.
- Bill announcements count as action only if the member describes what the bill does and why.

## 1. `x_risk`
**Claim:** *Advanced AI could cause a catastrophe for humanity (loss of control, extinction, or mass-casualty misuse such as AI-enabled bioweapons), and this deserves serious policy attention.* Everyday harms (jobs, bias, deepfakes, privacy, kids' safety) don't count here.

| Level | Test a statement must meet |
|---|---|
| 0 | Dismisses catastrophic AI risk as hype, sci-fi, doomerism or a distraction. |
| 1 | Mentions catastrophic risk but hedges or downplays it ("some worry about Terminator scenarios, but the real issue is…"). |
| 2 | Says in their own voice that catastrophic risk is a real concern, without asking for specific action. |
| 3 | Calls for a specific action *because of* catastrophic risk: legislation, safety testing, oversight, a hearing, an international agreement or a pause. |
| 4 | Says it is their top concern or among the most important issues facing the country or humanity (e.g. "as dangerous as nuclear weapons", "nothing matters more"). |

## 2. `agi_pilled`
**Claim:** *AI will soon become transformative on a historic scale, and possibly reach human-level or superhuman intelligence (AGI).* Only statements about AI's overall scale or trajectory get a label. Statements about a specific use or bill don't.

| Level | Test |
|---|---|
| 0 | Dismisses AGI or transformative-AI talk as hype or marketing. |
| 1 | Describes AI as an ordinary or incremental technology, one tool among many. |
| 2 | Says AI will transform the economy or society on a large scale (like the internet or the industrial revolution), without mentioning AGI. |
| 3 | Treats AGI, superintelligence or human-level AI as a real possibility within years to decades. |
| 4 | Says AGI or superintelligence is imminent (within a few years) or a civilizational turning point that should drive policy. |

## 3. `china_race`
**Claim:** *Winning the AI race against China should drive U.S. AI policy.* Only statements that mention China or a global AI race get a label.

| Level | Test |
|---|---|
| 0 | Rejects or criticizes race framing, or calls for cooperation with China on AI. |
| 1 | Mentions China in passing, without making it a reason for a position. |
| 2 | Gives competition with China as one reason among several for a position. |
| 3 | Gives competition with China as the main reason for a position. |
| 4 | Argues the race overrides other concerns, for example that safety rules should be dropped or avoided because of China. |

## 4. `ai_overall`
**Claim:** *AI will be good for Americans overall.* Only statements with a clear positive or negative view of AI's effects get a label. Neutral announcements don't.

| Level | Test |
|---|---|
| 0 | AI is mainly a threat or harm. |
| 1 | Acknowledges benefits, but the harms dominate. |
| 2 | Real promise and real risk, given equal weight. |
| 3 | Mainly an opportunity, with risks they treat as manageable. |
| 4 | Enthusiastic, with concerns minimal or dismissed. |

## 5. `regulation`
**Claim:** *The federal government should regulate AI companies more.* Only statements that take a position on AI rules get a label.

| Level | Test |
|---|---|
| 0 | Opposes AI regulation, or supports preempting or pausing state AI laws. |
| 1 | Prefers voluntary standards or light-touch rules, and is wary of new proposals. |
| 2 | Supports narrow rules on specific harms (deepfakes, kids' safety, transparency labels), but not broad frameworks. |
| 3 | Supports substantial obligations on AI companies: liability, audits, or safety testing of frontier models. |
| 4 | Supports comprehensive regulation, licensing of frontier AI, a new agency, or a pause. |

## Aggregation (fixed code)

- **Minimum evidence.** A member with fewer than 3 statements on AI in their own voice gets "not enough evidence" on every question.
- **x_risk, agi_pilled, china_race** (questions about how strongly something drives them):
  - **No labeled statements → 0** ("doesn't discuss it"), shown with its own reason.
  - Otherwise, the score is the **highest level reached by at least two statements**. If only one statement reaches the top level, the score is one step below that level, but never below the level that two statements do reach. This rewards consistency over one-off remarks.
- **ai_overall, regulation** (questions with two opposite ends):
  - The score is the **median** of the statement labels, rounded to the nearest whole step, with a tie rounding toward 2.
  - No labeled statements → "not enough evidence", because silence doesn't show which way someone leans.
- **Reason codes** are saved with every score and shown on the site: `silent`, `dismissive`, `one_off_capped`, `consistent`, `median_of_n`.
- **Recency.** Labels from the most recent 24 months are used when there are at least 3 of them; otherwise all labels are used. This tracks people whose views have changed.
