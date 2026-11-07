# Cascade calibration

Sample: 455 statements from 40 members (seed 7), each already labeled by Sonnet 5.5 and GPT-6.1 Sol.
Baseline: the two original judges give the same decision on 87.8% of (statement, question) pairs.

| Confidence threshold | Escalated labels | Cascade A vs Sonnet | Cascade B vs GPT | Mean |
|---|---|---|---|---|
| 3.0 | 43% | 88.7% | 92.8% | 90.7% |
| 3.5 | 58% | 88.7% | 93.8% | 91.3% |
| 4.0 | 65% | 88.7% | 94.0% | 91.3% |
| 4.5 | 89% | 88.7% | 94.3% | 91.5% |
| 5.0 | 94% | 88.7% | 94.3% | 91.5% |

Pick the cheapest threshold whose mean agreement is at least the baseline, and set `CONF_MIN` in `scripts/daily/label.py`. Astra tie-breaks are not simulated here (they are rare and only move labels toward a third opinion).

## Decision (2026-11-07)

`CONF_MIN = 3.0`. Below 3.0 the threshold changes nothing. About 42% of labels escalate anyway, because the three DeepSeek runs disagree or the label is 3+ on x-risk or AGI. Going up to 4.0 escalates 65% of labels, for only 0.5 points more agreement.

A fairer check uses only the (statement, question) pairs where Sonnet and GPT agree, so there is one clear answer:

| | Agreement with the two-judge answer |
|---|---|
| DeepSeek majority alone (slot A) | 95.7% |
| Cascade slot B (DeepSeek, or Sol when escalated) | 97.0% |

On all pairs, slot A matches Sonnet 88.7% of the time. The two original judges match each other 87.8% of the time.

Note: "Cascade B vs GPT" in the table above is generous. The original GPT judge and the reviewer are the same model (GPT-6.1 Sol).

An earlier run of this check was invalid. DeepSeek V4.1 Flash used all of its output tokens on reasoning and returned nothing on about 75% of calls. The fix sets its reasoning effort to "low" and allows 24k output tokens (`REASONING` in `label.py`). About 17% of DeepSeek run slots still come back empty; the majority vote and the Sol escalation cover these.
