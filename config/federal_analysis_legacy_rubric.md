<!-- rubric v3 -->
# Scoring rubric (v3)

Every question is a **claim**. A member's score is how strongly *they* back that claim in their own words, on one five-step scale with the same shape for every question:

| Level | Shape | Meaning |
|---|---|---|
| 0 | strongly disagree / absent | rejects the claim, or never engages with it |
| 1 | disagree / weak | engages, but downplays or hedges |
| 2 | neutral / moderate | backs the claim as a real consideration |
| 3 | agree | backs it strongly enough to want action on it |
| 4 | strongly agree | treats it as central or a top priority |

You are labeling **individual statements**. A fixed formula turns the labels into the member's score, so label each statement on its own merits.

## How to label a statement

1. **Judge meaning, not wording.** A statement passes a test if what it asserts meets the test, however it is phrased. Specific words or references (movies, "doomsday", "existential", "game-changer", "arms race") neither qualify nor disqualify a statement by themselves. Ask what the member is actually claiming.
2. **Own voice only.** Label a statement only for what the member says *they* believe or want. If they only report someone else's view (a CEO, experts, a study, a report), give it **no label**, unless they clearly adopt it: they say they share it, or they call for action because of it. Using someone else's warning only to attack an opponent is not adopting it.
3. **One level per question per statement:** the highest level whose test the statement fully meets. If it partly meets a test, use the level below.
4. **No label** when the statement does not address that question. Most statements address only one or two questions. Label a question only if this statement gives evidence about it.
5. Bill announcements count as calls for action only if the statement says what the bill does and why.

## 1. `x_risk`
**Claim:** *Advanced AI could cause a catastrophe for humanity, and this deserves serious policy attention.* Catastrophe means loss of human control over AI, human extinction or disempowerment, or misuse that could kill large numbers of people (AI-enabled biological, chemical or nuclear weapons, or AI-enabled attacks the statement says could cause mass casualties or society-wide collapse).
Not catastrophe: job losses, bias, privacy, deepfakes, scams, kids' safety, misinformation, energy use, ordinary cybersecurity (software vulnerabilities, hacking, protecting networks or infrastructure in general), or generic "national security" or military competition with no mass-casualty or civilization-scale scenario described.

| Level | Test |
|---|---|
| 0 | Rejects the idea that AI poses catastrophic risk (calls it hype, fiction, fearmongering, or a distraction from real issues). |
| 1 | Raises catastrophic risk but plays it down: treats it as remote, speculative, or less important than other issues. |
| 2 | Affirms that catastrophic risk is real or plausible, but does not ask for any specific response to it. |
| 3 | Asks for a specific response *because of* catastrophic risk: legislation, oversight, safety testing or evaluations, hearings, emergency powers, an international agreement, or slowing or pausing development. |
| 4 | Ranks catastrophic AI risk among the most important problems: their top concern, a threat comparable to nuclear war or pandemics, or something that should take priority over other AI goals. |

## 2. `agi_pilled`
**Claim:** *AI is on track to transform society on a historic scale, possibly reaching human-level or greater intelligence (AGI).*
Label only statements about AI's overall scale, capability or trajectory. Statements about a single use, harm, bill or industry get no label.

| Level | Test |
|---|---|
| 0 | Rejects claims of transformative AI or AGI (calls them hype, marketing, or overblown). |
| 1 | Describes AI as an ordinary or incremental technology, one tool among many, with no sign of expecting large change. |
| 2 | Says AI will change the economy or society on a very large scale (comparable to the internet or the industrial revolution), without claiming it will match or exceed human intelligence. |
| 3 | Treats AI matching or exceeding human intelligence in general (AGI, superintelligence) as a real possibility within years to decades. |
| 4 | Says AGI or superintelligence is near (within a few years) or is a civilizational turning point that should drive policy now. |

## 3. `china_race`
**Claim:** *Winning the AI competition with China should drive U.S. AI policy.*
Label only statements that mention China or an international AI race or competition.

| Level | Test |
|---|---|
| 0 | Rejects or criticizes race framing, or calls for cooperation or agreements with China on AI. |
| 1 | Mentions China or the competition without using it to justify a position. |
| 2 | Uses the competition as one reason among several for a position. |
| 3 | Uses the competition as the main reason for a position. |
| 4 | Argues the competition outweighs other concerns, e.g. that safety rules or limits should be avoided or dropped because of China. |

## 4. `ai_overall`
**Claim:** *AI will be good for Americans overall.*
Label only statements that express a view of **AI in general**: its overall effects on people, the economy or the country. A statement about one specific harm (e.g. deepfakes, scams, a lawsuit) or one specific benefit (e.g. a use in medicine) is **not** a view of AI overall, so it gets no label here, even if it is strongly worded. Neutral announcements, event notices and procedural statements also get no label.

| Level | Test |
|---|---|
| 0 | Presents AI as mainly a threat or harm. |
| 1 | Acknowledges some benefits, but treats harms as dominant. |
| 2 | Gives real benefits and real risks roughly equal weight. |
| 3 | Presents AI as mainly an opportunity, with risks treated as manageable. |
| 4 | Enthusiastic: benefits are the point, and concerns are minimal or dismissed. |

## 5. `regulation`
**Claim:** *The federal government should place more rules on AI and AI companies.*
Label only statements that take a position on rules for AI.

| Level | Test |
|---|---|
| 0 | Opposes regulating AI, or supports blocking or pausing state AI laws. |
| 1 | Prefers voluntary standards or light-touch rules, and warns against most new rules. |
| 2 | Supports narrow rules aimed at specific harms (e.g. deepfakes, kids' safety, disclosure or labeling), with no broad framework. |
| 3 | Supports substantial obligations on AI companies generally: liability, audits, licensing-style approval, or safety testing of advanced models. |
| 4 | Supports comprehensive regulation: a new regulator, licensing of frontier AI, or a pause or moratorium on advanced AI. |

## How labels become a score (fixed formula, not the model)

- **Minimum evidence:** fewer than 3 statements in total gives "not enough evidence" on every question.
- **Recency:** for each question, if at least 3 labeled statements fall in the last 24 months, only those are used.
- **x_risk, agi_pilled, china_race:** no labeled statements gives **0** ("doesn't discuss it"). Otherwise the score is the highest level that is **consistent** for them: reached by at least two statements, or by at least a third of their labeled statements on that question. If the top level is a one-off (one statement, and less than a third of their statements on the question), the score is one step below it. This rewards consistency over isolated remarks, without penalizing members who rarely speak.
- **regulation:** the strongest position they **consistently** take, using the same consistency rule as above. No labeled statements gives "not enough evidence".
- **ai_overall:** the **median** of the labels, with halves rounded toward the middle (2). No labeled statements gives "not enough evidence".
- **Two judges:** Claude Sonnet 5.5 and GPT-6.1 Sol each label every statement independently. The published score is the average of their two scores.
