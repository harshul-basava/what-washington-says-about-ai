"""Read credit metadata inside Actions without exporting a repository secret."""
import argparse
import json
import math
import os
from pathlib import Path
import sys

import httpx


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Invalid credit metadata')
    return float(value)


def summarize(key, credits, repository_remaining, required_credit):
    account = max(0, number(credits.get('total_credits')) - number(credits.get('total_usage')))
    repository = max(0, number(repository_remaining))
    required = number(required_credit)
    if required < 0:
        raise ValueError('Invalid required credit')
    # Missing cap fields cannot be interpreted as an unlimited key.
    if 'limit' not in key or 'limit_remaining' not in key:
        raise ValueError('Missing key limit metadata')
    key_remaining = key['limit_remaining']
    if key.get('limit') is not None and key_remaining is None:
        raise ValueError('Missing key allowance')
    limits = [account, repository]
    if key_remaining is not None:
        key_remaining = max(0, number(key_remaining))
        limits.append(key_remaining)
    guardrails = list(key.get('budgets') or [])
    if key.get('effective_budget'):
        guardrails.append(key['effective_budget'])
    guardrail_remaining = [max(0, number(b['remaining_usd'])) for b in guardrails]
    limits.extend(guardrail_remaining)
    available = min(limits)
    return {
        'status': 'checked',
        'account_remaining_usd': round(account, 6),
        'key_limit_remaining_usd': key_remaining,
        'guardrail_remaining_usd': min(guardrail_remaining) if guardrail_remaining else None,
        'repository_remaining_usd': round(repository, 6),
        'spendable_usd': round(available, 6),
        'required_credit_usd': required,
        'enough_for_requested_work': available >= required,
        'paid_calls': 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--required-credit', type=float, default=0)
    args = parser.parse_args()
    if not math.isfinite(args.required_credit) or args.required_credit < 0:
        parser.error('required-credit must be finite and nonnegative')
    key = os.environ.get('OPENROUTER_API_KEY', '')
    if not key:
        print(json.dumps({'status': 'unavailable', 'reason': 'missing_key', 'paid_calls': 0}))
        return 1
    report = {'status': 'unavailable', 'paid_calls': 0}
    try:
        with httpx.Client(timeout=30, follow_redirects=False) as client:
            data = {}
            for endpoint in ('key', 'credits'):
                response = client.get('https://openrouter.ai/api/v1/' + endpoint,
                                      headers={'Authorization': 'Bearer ' + key})
                if response.status_code != 200:
                    # Never include provider bodies, headers, or exception text in logs.
                    report.update(reason=endpoint + '_metadata_unavailable', http_status=response.status_code)
                    print(json.dumps(report))
                    return 1
                data[endpoint] = response.json()['data']
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import llm
        report.update(summarize(data['key'], data['credits'],
                                llm.BUDGETS['openrouter'] - llm.spent('openrouter'),
                                args.required_credit))
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        report.update(status='unavailable', reason='invalid_or_unavailable_metadata')
        print(json.dumps(report))
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
