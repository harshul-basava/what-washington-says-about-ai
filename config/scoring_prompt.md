<!-- scoring_prompt v1 -->
You are rating a U.S. politician's public views on AI, using **only** the statements below. These are verified quotes with dates and sources. They come from floor speeches, hearings, posts on X, and the web.

Follow this rubric exactly:

{rubric}

Instructions:
- Use only the statements. Ignore anything you know about the person, their party, or their ideology.
- For each dimension, give a 0–4 integer score, or "insufficient_evidence" if the statements don't address that dimension (see the rubric for when 1 is appropriate rather than insufficient_evidence).
- Cite the IDs of the statements you relied on most (1–5 per dimension).
- Each justification is 1–2 plain sentences.
- `summary`: 2–3 plain-English sentences on how this person talks about AI. Write it neutrally, as a careful journalist would.
- `evidence_strength`: "low" (few or thin statements), "medium", or "high" (many substantive statements covering several dimensions).
- `topics`: for **every** statement ID, give 1–3 topics from this fixed list: {topics}.

Person: {name}

Statements:
{statements}

Respond with JSON only, matching this schema:
{{"dimensions": {{"ai_overall": {{"score": 0-4 or "insufficient_evidence", "justification": "...", "statement_ids": ["s1", ...]}}, "agi_pilled": {{...}}, "x_risk": {{...}}, "china_race": {{...}}, "regulation": {{...}}}}, "summary": "...", "evidence_strength": "low|medium|high", "topics": {{"s1": ["..."], ...}}}}
