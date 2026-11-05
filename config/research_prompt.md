<!-- research_prompt v1 -->
You are researching public statements by **{name}** ({role}) about artificial intelligence.

Find **all** substantive public statements this person has made about AI that you can locate, from any period, in any public venue: interviews, press releases, op-eds, campaign websites, debates, podcasts, social media posts, letters, bill introductions with their own quoted words, hearings, floor speeches.

Topics that count: AI generally, AGI / superintelligence / transformative AI, AI risks (including catastrophic or existential risk, loss of control), AI and China / the AI race, AI regulation or deregulation, AI and jobs, deepfakes, kids' online safety and chatbots, data centers and energy for AI, AI copyright, AI in defense.

Rules:
- Only include words **this person** said or wrote, quoted **exactly** as they appear on the source page. No paraphrases. No quotes from other people, even about this person.
- Each statement needs the URL of the page where the exact quote appears, and the date if known.
- A statement should be one to five sentences long. Use "[...]" to join non-adjacent sentences from the same source.
- Do not pad. Returning zero statements is a perfectly fine answer if you cannot find any. Do not include trivial mentions (e.g. a press release that only lists "AI" in a list of topics).
- Do not characterize or score the person's views.
- Watch for people with the same name; make sure the statement is from this member of Congress.

Finish with only a JSON object, no other text after it:
```json
{{"statements": [{{"quote": "...", "url": "https://...", "date": "YYYY-MM-DD or YYYY-MM or YYYY or null", "venue": "short description"}}]}}
```
