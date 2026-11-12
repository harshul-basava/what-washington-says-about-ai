# Federal testimony and speech archives

The archive collector uses official indexes and existing verified source URLs. It makes no paid discovery searches. Initial indexes cover Federal Reserve speeches and testimony for 2023–2026 and Commerce speeches. The shared source inventory also includes official documents already found for selected officials and congressional hearing URLs. This is a bounded pilot, not complete federal archive coverage. Commerce currently blocks direct index access; no bypass or paid fallback runs.

`uv run python scripts/federal_archives.py discover` reads the indexes without model credentials. `uv run python scripts/federal_archives.py pilot` runs the fixed pilot. The original repository's `Federal archive pilot` workflow supplies its existing key without exposing it locally.

The pilot includes nine current officials across the Federal Reserve, Commerce and OSTP. Its cumulative limit is $10: at most $2 for extraction, with the remainder available for the five scores, policy judgments and Astra review. Retries retain the original ledger baseline. The pilot does not use X credentials. An Astra request for unavailable X context remains pending instead of making an unbudgeted call. No provider or repository cap changes.

The collector downloads each canonical document, then checks AI terms and current official names before extraction. One request covers all selected officials in a chunk. Source text, prompt and subject signatures invalidate stale results. Empty and rejected results also have persistent checkpoints. Unchanged documents reuse those checkpoints. Rejected rows stay visible as review gaps; the collector never calls an empty result evidence of no stance. Documents outside the page/chunk limits remain queued.

Accepted excerpts must pass the existing contiguous quote, attribution, date and role checks. Multi-speaker GovInfo hearings additionally require the existing reviewed speaker mapping. A witness list or nearby name does not authorize a quotation. The collector rejects overlapping excerpts on the same date and preserves stable evidence IDs. It never assigns institutional words to a person. Full source text and extraction responses stay in ignored `data/raw/federal_archives/`; public state contains URLs, hashes and progress only.

The existing daily federal job processes at most four archive documents and six eligible chunks under a $0.25 sub-limit. This amount counts inside its existing $1.50 collection limit. Ordinary daily judgments assess new evidence. The historical pilot has its own fixed cumulative allowance. No new recurring workflow is created.

The source inventory contains many documents unrelated to the selected pilot officials. Download counts, new excerpts, rejected rows, unfinished documents and costs are separate measures. Repeated excerpts from a single source do not establish broad coverage or independent samples.
