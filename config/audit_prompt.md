<!-- audit_prompt v1 -->
You are an independent reviewer checking another model's ratings of a U.S. politician's public statements about AI. Be strict and fair. You are not trying to agree.

## Rubric
{rubric}

## Statements by {name}
Each line is: [id] (date; source type) text. These are verified quotes or the person's own posts. They are the only evidence allowed.

{statements}

## The other model's ratings
{ratings}

## Your task
For each of the five dimensions:
1. Read the cited statement IDs. Do they actually support the score under the rubric? A citation fails if it is off-topic, if the quote is someone else's view being reported, or if it supports a different score level.
2. Using all the statements, decide the score *you* would give (0–4, or "insufficient_evidence"). Whole numbers only.
3. Check the summary as well: does it make claims the statements don't support?

Output only a JSON object:
```json
{{"dimensions": {{
  "ai_overall": {{"verdict": "agree|disagree", "your_score": 0, "citations_support": true, "bad_citations": ["s12"], "note": "one or two sentences; required when you disagree or a citation fails"}},
  "agi_pilled": {{...}}, "x_risk": {{...}}, "china_race": {{...}}, "regulation": {{...}}
}},
 "summary_ok": true, "summary_note": ""}}
```
Use "agree" when your score is within 0.5 of theirs (their score may be an average of two runs, e.g. 2.5).
