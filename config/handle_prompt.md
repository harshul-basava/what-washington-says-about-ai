<!-- handle_prompt v1 -->
Find the X (Twitter) account(s) of **{name}**, who just won the 2026 election for {role} ({party}).

Look at their campaign website, Wikipedia page, or news coverage. Include campaign, personal, and any current-office accounts (e.g. state legislator, mayor) that belong to this specific person. Do not guess handles. Only list a handle you saw on a page about this person.

Finish with only a JSON object:
```json
{{"handles": [{{"handle": "without @", "kind": "campaign|personal|office", "source_url": "https://..."}}]}}
```
Return an empty list if you could not find one.
