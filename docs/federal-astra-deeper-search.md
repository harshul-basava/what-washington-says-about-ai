# Deeper federal AI stance research — November 9, 2026

This follow-up covers the 32 eligible federal profiles that retained no AI overall stance after the first Astra audit. It uses the same Congress rubric and score formula. A profile still needs three verified excerpts in total. A single clear general AI stance can supply the AI overall label within that corpus.

## Research depth

The web search used 65 queries: two different searches for every profile, plus one focused follow-up. The search requested five results per query. Researchers selected 122 distinct source URLs and retrieved their page text. X source leads added 11 more web URLs. Astra reviewed the supplied page text for each profile, including pages that supplied no qualifying quote. Some pages contained only a video description, a short abstract, or limited text. A retrieval does not prove that the full underlying speech or interview was available.

The official X API ran 50 queries. These included 34 searches across 17 verified account ownership intervals for 16 profiles. Another 16 profiles received exact-name mention searches. Account searches used both general AI outlook terms and additional AI terms. Searches covered January 1, 2023 through November 8, 2026, subject to each verified ownership interval.

All account queries reached their endpoint. Eleven mention queries reached their endpoint. Five high-volume mention queries used a sample limit: Jay Clayton, Joshua Rudd, Kevin Hassett, Jamieson Greer, and John Ratcliffe. The collector checks the limit after each page. Clayton returned 604 posts before the limit was introduced; the other samples contain 200–213 posts. These samples do not constitute exhaustive mention searches.

The API returned 1,969 post reads, including repeat matches across queries. The verified account results contained 49 distinct authored posts. The corpus already contained 43. Five new posts contained links without usable authored text. Astra reviewed the remaining new DHS post and found no general AI stance. Mention posts supplied source leads only; they did not establish the named person's authorship.

## Evidence and final review

The research added 14 verified web excerpts across nine profiles. Each quote passed an exact source check, an attribution check, and a date check. One complete Todd Blanche quotation contains seven words. The researcher verified it directly and documented the exception to the collector's eight-word minimum. This exception does not change the stance rubric or the minimum evidence requirement.

Astra first reviewed the retrieved pages for potential evidence. The final audit then reviewed all 476 excerpts across the 32 profiles, with verified wider context where available. It received no previous model answers. Accepted findings require confidence of at least 3 out of 5. Confidence describes model certainty, not measured accuracy.

The final Astra decision controls AI overall for each reviewed excerpt. It can add a supported stance or remove an unsupported base label. The original model assessments and prior Astra review remain in the analysis cache. The other four scores retain the normal analysis process. The nine profiles with new evidence also received fresh regulation assessments and cited summaries.

Historical dates remain explicit. Paul Christiano's new excerpt dates from 2014. The Defense strategy dates from June 2022. The new DHS source dates from 2024. One Hassett source provides no verified date. These records do not establish a new statement by the current administration.

## Reproduction and limits

The [research manifest](../data/federal_stance_search.json) records searches, source URLs, source review reasons, accepted evidence, and X coverage. The [final Astra audit](../data/federal_stance_search_review.json) records each judgment and its provenance. Full retrieved text remains in ignored local caches. The [X checkpoint](../data/federal_stance_x_search.json) records query bounds, page counts, and sample limits.

Use `federal_stance_review.py --audit data/federal_stance_search_review.json` with the `review`, `context`, or `apply` command to operate this separate audit. The original 33-profile audit remains unchanged. The manual `federal-stance-search.yml` workflow uses the original repository's X secret and retains the existing $2 batch cap. It does not run daily.

Daily updates retain the accepted judgments while their evidence and analysis inputs remain valid. All 97 eligible profiles continue through the existing daily collection and analysis process. New excerpts receive the normal DeepSeek/Sol/Astra analysis. Daily updates do not repeat this paid research audit. Reconstructed histories reflect the corrected labels; earlier observed snapshots remain unchanged.

## Results

Ten profiles gained an AI overall score. Twenty-two still lack a qualifying general stance. All 3,513 federal excerpts have complete analysis; no labels, regulation categories, or summaries remain pending. The federal roster remains 97 profiles. Of these, 56 have an AI overall score, 22 lack a qualifying stance despite at least three excerpts, nine have too few excerpts, and ten have no evidence.

| Profile | New web excerpts | AI overall score, 0–4 | Final audit confidence, 1–5 |
|---|---:|---:|---:|
| JD Vance | 3 | 3.0 | 4 |
| Howard Lutnick | 2 | 4.0 | 4 |
| Jeffrey Kessler | 0 | No qualifying stance | 5 |
| Jay Clayton | 0 | No qualifying stance | 4 |
| Joshua Rudd | 0 | No qualifying stance | 5 |
| Bureau of Industry and Security (BIS) | 0 | 2.0 | 5 |
| Superintelligence Task Force / Super Intelligence Force | 0 | No qualifying stance | 5 |
| Carter Farmer | 0 | No qualifying stance | 4 |
| Kevin Hassett | 2 | 4.0 | 4 |
| Office of the National Cyber Director | 0 | No qualifying stance | 4 |
| National Security Council | 0 | No qualifying stance | 4 |
| David Peters | 0 | No qualifying stance | 5 |
| Arvind Raman | 0 | No qualifying stance | 5 |
| Paul Christiano | 1 | 1.0 | 4 |
| Paras Malik | 2 | 3.0 | 4 |
| Christopher Pilkerton | 0 | No qualifying stance | 4 |
| Jamieson Greer | 0 | No qualifying stance | 5 |
| Brian Epley | 0 | No qualifying stance | 5 |
| Amy Ritualo | 0 | No qualifying stance | 4 |
| Pete Hegseth | 0 | No qualifying stance | 4 |
| John Ratcliffe | 0 | No qualifying stance | 5 |
| Todd Blanche | 1 | 4.0 | 5 |
| Stephen Weiss | 0 | No qualifying stance | 5 |
| Mark Meador | 1 | 2.0 | 5 |
| Edward Forst | 0 | No qualifying stance | 4 |
| Department of War / Defense | 1 | 3.0 | 4 |
| Chief Digital and Artificial Intelligence Office | 0 | No qualifying stance | 5 |
| Office of the Director of National Intelligence | 0 | No qualifying stance | 5 |
| Central Intelligence Agency | 0 | No qualifying stance | 5 |
| Department of Homeland Security | 1 | 2.0 | 4 |
| Department of Justice Super Intelligence Task Force | 0 | No qualifying stance | 5 |
| Federal Acquisition Service | 0 | No qualifying stance | 4 |

These scores summarize the available dated record. They do not establish a current position from an old statement. In particular, Christiano’s historical score comes from a 2014 essay.

The ledger records $11.966930 for model work and $10.115 for X research during this follow-up. The Exa connector does not report its charges to the project ledger, so these amounts exclude any Exa charges. No budget cap increased.
