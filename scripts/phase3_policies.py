"""Policy judgments. `plan` and `build` are offline; only `label` makes paid calls."""
import argparse
import json
import math
import random
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import policy_judgments as p
import policy_cascade as cascade

MAX_TOKENS = 10000


def select_subject_scope(subjects, scope):
    if scope == 'all':
        return subjects
    branch = 'executive' if scope == 'executive' else 'legislative'
    return [s for s in subjects if s['branch'] == branch]


def select_scope(items, subjects, scope):
    if scope == 'all':
        return items
    ids = {s['id'] for s in select_subject_scope(subjects, scope)}
    return [s for s in items if s['person_id'] in ids]


def select_people(items, limit):
    if not limit:
        return items
    # Cover each target, then fill a deterministic sample; the pilot is not an accuracy estimate.
    chosen = []
    for target in sorted({t for s in items for t in s["targets"]}):
        pid = next(s["person_id"] for s in items if target in s["targets"])
        if pid not in chosen:
            chosen.append(pid)
    rest = sorted({s["person_id"] for s in items} - set(chosen))
    random.Random(20261107).shuffle(rest)
    ids = set((chosen + rest)[:limit])
    return [s for s in items if s["person_id"] in ids]


def jobs(items, saved, registry, rubric, batch_size):
    out = []
    valid = {s["key"]: p.valid_judges(s, saved, registry, rubric) for s in items}
    for judge in p.JUDGES:
        missing = [s for s in items if judge not in valid[s["key"]]]
        for start in range(0, len(missing), batch_size):
            out.append((judge, missing[start:start + batch_size]))
    return out


def label(work, saved, registry, rubric, args, strategy=None, confidence_prompt="", baseline=None):
    # Import the existing paid-call gateway only for the explicit label command.
    import llm
    if not math.isfinite(args.max_cost) or args.max_cost <= 0 or not 1 <= args.workers <= 8:
        raise ValueError("Use a positive max-cost and 1–8 workers")
    if not llm.os.environ.get("OPENROUTER_API_KEY"):
        raise ValueError("OPENROUTER_API_KEY is required only for label")
    # Public metadata GET, not a paid inference call. Fail closed if prices are unavailable.
    r = llm.httpx.get("https://openrouter.ai/api/v1/models", timeout=30)
    r.raise_for_status()
    model_ids = cascade.models(strategy) if strategy else p.JUDGES
    metadata = {m["id"]: m for m in r.json()["data"] if m["id"] in model_ids.values()}
    prices = {model: m["pricing"] for model, m in metadata.items()}
    for model in model_ids.values():
        if model not in prices:
            raise ValueError(f"Configured model is unavailable: {model}")
    baseline = llm.spent("openrouter") if baseline is None else baseline
    from model_budget import Budget
    budget = Budget(args.max_cost, getattr(args, 'daily', False), metadata, llm)
    budget.baseline = baseline

    def run(job):
        judge, items = job
        model = model_ids[judge]
        messages = cascade.messages(items, registry, rubric, confidence_prompt, judge) if strategy else p.messages(items, registry, rubric)
        try:
            supported = metadata[model].get("supported_parameters", [])
            options = {"reasoning": {"effort": "medium"}} if strategy and "reasoning" in supported else {}
            if not strategy or "temperature" in supported:
                options["temperature"] = 0
            tag = ('daily_' if getattr(args, 'daily', False) else '') + f"policy_{'cascade' if strategy else 'v1'}_{judge}"
            result = budget.call(model, messages, MAX_TOKENS, tag, **options)
            try:
                labels = (cascade.validate_response if strategy else p.validate_response)(result["choices"][0]["message"]["content"], items, registry)
            except ValueError as exc:
                # These fixed validation messages never include raw provider bodies.
                detail = f"{exc.msg}, line {exc.lineno}, column {exc.colno}" if isinstance(exc, json.JSONDecodeError) else str(exc)
                return judge, items, None, f"Invalid judgment ({detail}); rerun to resume", None
            return judge, items, labels, None, result.get("id")
        except Exception as exc:
            # Do not echo provider bodies, keys, or untrusted response text into logs.
            return judge, items, None, f"{type(exc).__name__}: batch incomplete; rerun to resume", None

    errors = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run, job) for job in work]
        for number, future in enumerate(as_completed(futures), 1):
            judge, items, labels, error, generation_id = future.result()
            if error:
                errors += 1
                print(f"{number}/{len(work)} {judge}: {error}", flush=True)
                continue
            for item in items:
                if strategy:
                    for target, value in labels[item["key"]].items():
                        cascade.save_result(saved, item, target, judge, value, registry, rubric, confidence_prompt, strategy, generation_id)
                    continue
                saved.setdefault("results", {}).setdefault(item["key"], {})[judge] = {
                    "model": p.JUDGES[judge], "input_hash": p.fingerprint([item], registry, rubric, p.JUDGES[judge]),
                    "judged_at": datetime.now(timezone.utc).isoformat(), "labels": labels[item["key"]]}
            p.write_json(ROOT / ("data/policy_cascade.json" if strategy else "data/policy_judgments.json"), saved)
            print(f"{number}/{len(work)} {judge}: {len(items)} statements; run cost ${llm.spent('openrouter') - baseline:.3f}", flush=True)
    cost = llm.spent("openrouter") - baseline
    print(f"Run cost ${cost:.3f}; {errors} incomplete batches. Saved results resume automatically.")
    return errors


def label_cascade(items, saved, registry, rubric, confidence_prompt, strategy, args):
    import llm
    baseline = llm.spent("openrouter")
    errors = 0
    for role in cascade.ROLES:
        batch_size = args.batch_size if role == "deepseek" else min(args.batch_size, 4)
        work = cascade.jobs(items, saved, registry, rubric, confidence_prompt, strategy, role, batch_size)
        if work:
            print(f"{role}: {len(work)} batches", flush=True)
            errors += label(work, saved, registry, rubric, args, strategy, confidence_prompt, baseline)
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "label", "build"))
    parser.add_argument("--limit-people", type=int)
    parser.add_argument('--scope', choices=('all', 'congress', 'executive'), default='all')
    parser.add_argument('--ids', help='Comma-separated eligible subject IDs for plan or label')
    parser.add_argument('--daily', action='store_true', help='Use daily spend tags and reserve against the monthly cap')
    parser.add_argument("--targets", help="Comma-separated registry IDs; filters candidate statements, not output labels")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-cost", type=float, default=5, help="Maximum additional USD for this run; reserves in-flight calls")
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 40 or (args.limit_people is not None and args.limit_people < 1):
        parser.error("batch-size must be 1–40; limit-people must be positive")
    if args.command == "build":
        if args.ids is not None:
            parser.error('--ids applies only to plan and label')
        result = p.build(ROOT)
        print(f"Built {len(result['policies'])} policies for {len(result['members'])} people from tracked inputs.")
        return
    subjects = select_subject_scope(p.subjects.load_subjects(ROOT), args.scope)
    if args.ids is not None:
        wanted = set(args.ids.split(','))
        if not wanted <= {s['id'] for s in subjects}:
            parser.error('Unknown subject ID for the selected scope')
        subjects = [s for s in subjects if s['id'] in wanted]
    registry = p.load_registry(ROOT)
    rubric = (ROOT / "config/policy_rubric.md").read_text()
    items = p.candidates(ROOT, registry, selected_subjects=subjects)
    if args.targets:
        wanted = set(args.targets.split(","))
        known = {t["id"] for t in registry["policies"]}
        if not wanted <= known:
            parser.error("Unknown policy ID")
        items = [s for s in items if wanted.intersection(s["targets"])]
    items = select_people(items, args.limit_people)
    target_counts = Counter(t for s in items for t in s["targets"])
    strategy = cascade.load_strategy(ROOT)
    confidence_prompt = (ROOT / "config/policy_confidence.md").read_text() if strategy else ""
    path = ROOT / ("data/policy_cascade.json" if strategy else "data/policy_judgments.json")
    saved = p.read_json(path) if path.exists() else {"schema_version": 1, "results": {}}
    if strategy:
        work = [job for role in cascade.ROLES for job in cascade.jobs(items, saved, registry, rubric, confidence_prompt, strategy, role, args.batch_size if role == "deepseek" else min(args.batch_size, 4))]
    else:
        work = jobs(items, saved, registry, rubric, args.batch_size)
    chars = sum(sum(len(m["content"]) for m in p.messages(batch, registry, rubric)) for _, batch in work)
    pairs = sum(len(s["targets"]) for _, batch in work for s in batch)
    # Indicative prices checked 2026-11-07. The runner checks live prices before spending.
    estimate = chars / 3.5 * 0.000002 + pairs * 90 * 0.00001
    print(json.dumps({"people": len({s['person_id'] for s in items}), "candidate_statements": len(items),
                      "candidate_pairs": dict(target_counts), "uncached_requests": len(work),
                      "estimated_cost_usd": None if strategy else round(estimate, 2),
                      "strategy": strategy, "review_note": "Astra work is known only after DeepSeek returns confidence; label checks live prices." if strategy else None}, indent=2), flush=True)
    if args.command == "label":
        errors = (label_cascade(items, saved, registry, rubric, confidence_prompt, strategy, args) if strategy else label(work, saved, registry, rubric, args)) if work else 0
        p.build(ROOT)
        if errors:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
