"""Apply the authorized $200 -> $350 lifetime cap to the key's own workspace."""
import argparse
import json
import math
import os
import re

import httpx


BASE = 'https://openrouter.ai/api/v1'


class MetadataError(RuntimeError):
    def __init__(self, status_code, stage):
        self.status_code = status_code
        self.stage = stage
        super().__init__('OpenRouter budget operation did not complete')


def request(client, method, path, stage, **kwargs):
    response = client.request(method, BASE + path, **kwargs)
    if response.status_code != 200:
        raise MetadataError(response.status_code, stage)
    return response.json()['data']


def lifetime(rows):
    return [row for row in rows if row.get('reset_interval') in (None, 'lifetime')]


def other_limits(rows):
    result = {}
    for row in rows:
        interval = row.get('reset_interval')
        if interval in (None, 'lifetime'):
            continue
        identifier, cap = row.get('id'), row.get('limit_usd')
        if (interval not in ('daily', 'weekly', 'monthly') or
                not isinstance(identifier, str) or not identifier.strip() or
                isinstance(cap, bool) or not isinstance(cap, (int, float)) or
                not math.isfinite(cap) or cap <= 0 or identifier in result):
            raise ValueError('Invalid other interval metadata')
        result[identifier] = (interval, cap)
    return result


def raise_workspace_cap(client):
    key = request(client, 'GET', '/key', 'read_key')
    workspace = key.get('workspace_id', '')
    if not isinstance(workspace, str) or not re.fullmatch(r'[0-9a-fA-F-]{36}', workspace):
        raise ValueError('Missing workspace identity')
    expected = lifetime([b for b in key.get('budgets', []) if b.get('scope') == 'workspace'])
    if (len(expected) != 1 or expected[0].get('limit_usd') not in (200, 350) or
            not isinstance(expected[0].get('budget_id'), str) or not expected[0]['budget_id'].strip()):
        raise ValueError('Unexpected workspace cap')
    path = '/workspaces/' + workspace + '/budgets'
    before = request(client, 'GET', path, 'read_budgets')
    current = lifetime(before)
    if (len(current) != 1 or current[0].get('workspace_id') != workspace or
            current[0].get('id') != expected[0].get('budget_id') or
            current[0].get('limit_usd') != expected[0]['limit_usd']):
        raise ValueError('Workspace budget identity or cap changed')
    old_cap = current[0]['limit_usd']
    unchanged_limits = other_limits(before)
    if old_cap == 350:
        return {'status': 'already_set', 'lifetime_cap_usd': 350, 'paid_calls': 0}
    # Do not send include_byok_in_budgets or touch any other budget interval.
    request(client, 'PUT', path + '/lifetime', 'update_budget', json={'limit_usd': 350})
    after = request(client, 'GET', path, 'verify_budgets')
    updated = lifetime(after)
    if (len(updated) != 1 or updated[0].get('limit_usd') != 350 or
            updated[0].get('id') != current[0]['id'] or
            updated[0].get('workspace_id') != workspace):
        raise ValueError('Updated workspace budget not verified')
    if unchanged_limits != other_limits(after):
        raise ValueError('Other workspace budget limits changed during the operation')
    return {'status': 'updated', 'previous_lifetime_cap_usd': 200,
            'lifetime_cap_usd': 350, 'other_interval_limits_unchanged': True, 'paid_calls': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply-authorized-350', action='store_true', required=True)
    parser.parse_args()
    key = os.environ.get('OPENROUTER_API_KEY', '')
    if not key:
        print(json.dumps({'status': 'not_completed', 'reason': 'missing_key', 'paid_calls': 0}))
        return 1
    try:
        with httpx.Client(headers={'Authorization': 'Bearer ' + key}, timeout=30,
                          follow_redirects=False) as client:
            report = raise_workspace_cap(client)
    except MetadataError as exc:
        print(json.dumps({'status': 'not_completed', 'http_status': exc.status_code,
                          'stage': exc.stage, 'paid_calls': 0}))
        return 1
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
        print(json.dumps({'status': 'not_completed', 'reason': 'operation_or_verification_failed', 'paid_calls': 0}))
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
