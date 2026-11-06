<!-- label_prompt v1 -->
You are labeling public statements by a U.S. politician, {name}, for a study of how members of Congress talk about AI. Apply the rubric below exactly. Read each statement for what it actually claims.

{rubric}

## Statements
Each line is: [id] (date; source type) text

{statements}

## Output
Return only a JSON object. Include **only** statements that get at least one label, and only the questions they address:
```json
{{"labels": {{"s12": {{"x_risk": 3, "regulation": 3}}, "s40": {{"china_race": 2}}}}}}
```
Valid questions: x_risk, agi_pilled, china_race, ai_overall, regulation. Valid levels: 0, 1, 2, 3, 4. If no statement gets a label, return {{"labels": {{}}}}.
