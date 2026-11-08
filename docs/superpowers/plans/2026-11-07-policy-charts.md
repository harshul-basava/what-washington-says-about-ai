# Policy charts

The user requested visualizations of the policy judgments. Add them to the existing policy explorer, using its data and filters. No new model calls or deployment are needed.

Design choices: an overview across ten policies, a party comparison for the selected policy, a statement timeline, and detail-label counts for exports, auditors, and China. Use the existing page theme and no additional network libraries. Overview rows select the corresponding policy. Keep the quote explorer below the charts.

Accuracy rules:
- Count each member once in member charts. Show the relevant-evidence count against the filtered roster alongside each normalized stance bar.
- Keep incomplete assessments out of stance distributions and report them separately. Missing evidence never becomes opposition.
- Use party, population, and name filters for charts. The stance filter applies only to the member list, so it cannot make a chart tautological.
- Count statements in the timeline, not members or inferred sentiment scores. Include zero-count periods between observed dates. Exclude year-only and missing dates and report that count.
- Count detail labels on statements. Separate labels applied by both judges from labels applied by just one. Labels alone do not imply endorsement.
- Generate compact chart records offline from validated judgments. Match summary and chart revisions to prevent stale charts.

Steps:
- [x] Test export consistency, aggregation, incomplete dates, sparse data, and chart geometry.
- [x] Implement the offline chart export and responsive charts.
- [x] Connect charts to the existing filters and policy selection.
- [x] Check desktop, phone, theme changes, and quote navigation in the browser.
- [x] Run all tests and obtain one code review under the requesting-code-review skill.

Validation: 18 Python tests and 10 JavaScript tests pass. JavaScript syntax checks and `git diff --check` pass. The offline export build succeeds without an API key. The independent review matched all 2,844 compact records with detailed records and summaries. Its one minor contrast finding led to darker count text.

Browser checks covered desktop, 390-pixel and 320-pixel widths, both themes, policy selection, party and stance filters, empty results, sparse evidence, and source quote expansion. The policy section has no horizontal overflow at either phone width. Timeline labels do not overlap. Browser error logs are empty. Changes remain local; this task adds no paid model calls or deployment.
