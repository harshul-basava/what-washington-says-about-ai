# Confidence assessment v1

For each statement-policy pair, also return `confidence` as a finite JSON number from 0 to 1 and `confidence_reason` as one short sentence.

Confidence means your estimated probability that a careful human reviewer applying this rubric would accept the entire classification: the target identity, relevance, stance, and all selected additional labels. It does not measure the strength of the speaker's endorsement, your agreement with that speaker, the importance of a policy, or the quantity of evidence. A clear neutral, unclear, or not_relevant classification can have high confidence. Use lower confidence when target identity, speaker attribution, missing context, stance direction, or an additional label remains uncertain. Do not invent certainty or adjust your score to avoid review. These self-reported scores require empirical calibration.

Keep `reason` tied to the evidence. Use `confidence_reason` to state the main source of certainty or uncertainty. Return all requested pairs, including not_relevant. Follow this expanded JSON schema instead of the shorter example in the shared rubric:

{"judgments":[{"key":"PERSON|s1","targets":{"policy_id":{"stance":"support","reason":"The speaker asks Congress to pass this bill.","facets":[],"confidence":0.95,"confidence_reason":"The statement names the bill and explicitly endorses it."}}}]}
