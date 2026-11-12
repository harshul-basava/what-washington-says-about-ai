# Federal testimony and speech archives

The archive collector uses official indexes and existing verified source URLs. It makes no paid discovery searches. Initial indexes cover Federal Reserve speeches and testimony for 2023–2026 and Commerce speeches. The shared source inventory also includes official documents already found for selected officials and congressional hearing URLs. This is a bounded pilot, not complete federal archive coverage. Commerce currently blocks direct index access; no bypass or paid fallback runs.

`uv run python scripts/federal_archives.py discover` reads the indexes without model credentials. `uv run python scripts/federal_archives.py pilot` runs the fixed pilot. The original repository's `Federal archive pilot` workflow supplies its existing key without exposing it locally.

The pilot includes nine current officials across the Federal Reserve, Commerce and OSTP. Its cumulative limit is $10: at most $2 for extraction, with the remainder available for the five scores, policy judgments and Astra review. Retries retain the original ledger baseline. The pilot does not use X credentials. An Astra request for unavailable X context remains pending instead of making an unbudgeted call. No provider or repository cap changes.

The collector downloads each canonical document, then checks AI terms and current official names before extraction. One request covers all selected officials in a chunk. Source text, prompt and subject signatures invalidate stale results. Empty and rejected results also have persistent checkpoints. Unchanged documents reuse those checkpoints. Rejected rows stay visible as review gaps; the collector never calls an empty result evidence of no stance. Documents outside the page/chunk limits remain queued.

Accepted excerpts must pass the existing contiguous quote, attribution, date and role checks. Multi-speaker GovInfo hearings additionally require the existing reviewed speaker mapping. A witness list or nearby name does not authorize a quotation. The collector rejects overlapping excerpts on the same date and preserves stable evidence IDs. It never assigns institutional words to a person. Full source text and extraction responses stay in ignored `data/raw/federal_archives/`; public state contains URLs, hashes and progress only.

The existing daily federal job processes at most four archive documents and six eligible chunks under a $0.25 sub-limit. This amount counts inside its existing $1.50 collection limit. Ordinary daily judgments assess new evidence. The historical pilot has its own fixed cumulative allowance. No new recurring workflow is created.

The source inventory contains many documents unrelated to the selected pilot officials. Download counts, new excerpts, rejected rows, unfinished documents and costs are separate measures. Repeated excerpts from a single source do not establish broad coverage or independent samples.

## Pilot results, November 12, 2026

The first collection pass added 181 verified excerpts from 23 speeches. Five Federal Reserve officials supplied all new excerpts. The selected sources span September 2023 through October 2026. The official evidence count rose from 2,850 to 3,031.

| Official | New excerpts | Speeches |
|---|---:|---:|
| Michael S. Barr | 65 | 7 |
| Lisa D. Cook | 51 | 6 |
| Christopher J. Waller | 27 | 4 |
| Michelle W. Bowman | 23 | 4 |
| Philip N. Jefferson | 15 | 2 |

The collector checked 70 documents and downloaded 69. It made 34 extraction requests and no paid discovery searches. Collection cost $0.078488. It rejected nine candidate rows and suppressed 30 duplicate excerpts. The [pilot audit](../data/federal_archive_pilot.json) records cumulative costs and review status. The original $10 allowance and its $2 extraction sub-limit remain unchanged.

The completed pilot cost **$2.603508**, leaving $7.396492 of its allowance unused. The [completed workflow](https://github.com/harshul-basava/what-washington-says-about-ai/actions/runs/43168816928) saved the evidence, judgments and site data.

| Stage | Actual model cost |
|---|---:|
| Archive extraction | $0.078488 |
| Five scores, regulation categories and summaries | $0.637263 |
| Named-policy judgments | $0.000202 |
| Independent Astra stance audit, including context follow-ups | $1.887555 |
| Total | **$2.603508** |

All 234 existing and new excerpts for these five officials completed the ordinary analysis pipeline. This includes the five scores, 23 regulation categories and cited summaries. Named-policy judgments also completed. Independent Astra review checks overall AI stance and retrieves additional source context when needed. Identical context now appears once per request, with separate references and attribution metadata for each excerpt. This saves input tokens without removing source text or weakening verification.

Astra completed all five profile reviews and recorded 26 supported stance findings. No context request remains pending. The resumed run reused all completed ordinary judgments and made no new ordinary-analysis requests. The [offline cache check](../data/federal_archive_cache_check.json) matched all 181 new excerpts against 23 source snapshots. It made zero model requests and found no errors. The test suites passed 322 Python tests and 74 JavaScript tests.

The collector discovered 959 document URLs. Its bounded pass left 890 documents outside the completed queue. Two source documents retain rejected rows for review. Commerce's archive index returned HTTP 403. One congressional hearing PDF also failed retrieval. No new testimony excerpts entered this pilot. These results show useful yield from Federal Reserve speeches; they do not establish the yield or coverage of other agencies.

## Source spot checks

The assistant checked one new excerpt per official against the primary page. Each excerpt matched the source text, named speaker and date. These five checks supplement the automated checks. They are not a human validation study or an estimate of overall accuracy.

| Evidence ID | Primary source | Context check |
|---|---|---|
| `exec_michelle_w_bowman/s15` | [November 22, 2024 speech](https://www.federalreserve.gov/newsevents/speech/bowman20241122a.htm) | The paragraph discusses costs of excessive regulation. Later paragraphs also discuss risks from insufficient regulation. |
| `exec_michael_s_barr/s15` | [February 18, 2025 speech](https://www.federalreserve.gov/newsevents/speech/barr20250218a.htm) | The excerpt appears in his recommendations after two hypothetical scenarios. It is his recommendation, not a scenario outcome. |
| `exec_christopher_j_waller/s6` | [October 15, 2025 speech](https://www.federalreserve.gov/newsevents/speech/waller20251015a.htm) | The preceding sentences explicitly discuss AI benefits and misuse. The excerpt contains his policy recommendation. |
| `exec_philip_n_jefferson/s15` | [November 7, 2025 speech](https://www.federalreserve.gov/newsevents/speech/jefferson20251107a.htm) | The excerpt describes potential economic effects. Its wording alone does not establish an overall positive or negative stance. |
| `exec_lisa_d_cook/s7` | [September 22, 2023 speech](https://www.federalreserve.gov/newsevents/speech/cook20230922a.htm) | Her broad optimism depends on addressing the risks described immediately before it. The excerpt preserves that condition. |

The offline `check-cache` command requires every pilot-added statement exactly once. It checks every excerpt against the source snapshot and its hash. It also checks completed extraction checkpoints without allowing new requests or evidence writes. Missing evidence, changed sources and incomplete checkpoints fail the check. The command excludes unrelated daily documents.
