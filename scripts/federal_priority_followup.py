"""Resume the fixed priority follow-up without resetting its combined allowance."""
import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MANIFEST = 'data/federal_priority_followup.json'


def allowances(budget, model_spend, x_spend):
    values = [*budget.values(), model_spend, x_spend]
    if not all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in values):
        raise ValueError('Invalid budget')
    model_delta = model_spend - budget['openrouter_baseline']
    x_delta = x_spend - budget['x_baseline']
    if min(model_delta, x_delta) < -0.000001:
        raise ValueError('Cost ledger predates the fixed baseline')
    model_delta, x_delta = max(0, model_delta), max(0, x_delta)
    # A separately documented daily-run reservation still counts against the
    # combined limit, but is not a request from this dedicated X search.
    other_x = budget.get('other_x_reserved', 0)
    if other_x > x_delta + 0.000001:
        raise ValueError('Unbacked other-X reservation')
    search_delta = max(0, x_delta - other_x)
    remaining = max(0, budget['combined_limit'] - model_delta - x_delta)
    return {'spent': model_delta + x_delta, 'remaining': remaining,
            'x_search': max(0, min(remaining, budget['x_search_limit'] - search_delta)),
            # The existing Astra runner permits three context fetches of at most $0.50.
            'models': max(0, remaining - budget['astra_x_context_reserve'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['plan', 'x', 'models'])
    args = parser.parse_args()
    import federal_analysis as analysis
    import llm
    manifest = analysis.read(ROOT / MANIFEST)
    budget = allowances(manifest['budget'], llm.spent('openrouter'), llm.spent('x'))
    ids = manifest['target_ids']
    subjects, _ = analysis.inputs(ROOT)
    if len(ids) != len(set(ids)) or not set(ids) <= {s['id'] for s in subjects}:
        raise ValueError('Follow-up targets must remain eligible and unique')
    print(json.dumps({'stage': args.stage, 'targets': len(ids), 'allowance': budget}), flush=True)
    if args.stage == 'x':
        if budget['x_search'] <= 0:raise ValueError('X search allowance exhausted')
        from federal_stance_search import collect_x
        collect_x(ROOT, max_cost=budget['x_search'], manifest_path=MANIFEST,
                  state_path='data/federal_priority_x_search.json',
                  raw_path='data/raw/federal_priority_followup', max_pages_per_job=3)
    elif args.stage == 'models':
        if budget['models'] <= 0:raise ValueError('Model allowance exhausted')
        from scripts.federal_expansion_runner import run
        run(ROOT, 'priority_followup', ids, ['analysis', 'policies', 'astra'], budget['models'], 12)


if __name__ == '__main__':main()
