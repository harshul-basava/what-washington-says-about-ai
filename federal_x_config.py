"""Shared federal X query and checkpoint identity for collection and coverage."""
import hashlib
import json
from datetime import datetime, timezone

KEYWORDS = '(AI OR "artificial intelligence" OR AGI OR superintelligence OR "super intelligence" OR OpenAI OR Anthropic OR "AI chips" OR "export controls" OR "FRONTIER Act" OR "Kill Switch Act" OR "Stop Stealing Our Chips" OR "independent verification")'

# Fixed public error categories; never copy provider titles, details, or values.
PROBLEM_TYPES = frozenset({'invalid-request', 'resource-not-found', 'not-authorized-for-resource',
    'not-authorized-for-field', 'field-unauthorized', 'field-hydration-failure', 'disallowed-resource',
    'client-forbidden', 'usage-capped', 'rate-limit-exceeded', 'internal-error'})


def provider(config):
    value = config.get('provider', 'emusks')
    if value not in ('emusks', 'x_api'):
        raise ValueError('Unknown federal X provider')
    return value


def state_file(config):
    return 'federal_x_api_state.json' if provider(config) == 'x_api' else 'federal_x_state.json'


def fingerprint(account):
    # A changed query or sourced account definition requires a fresh search.
    return hashlib.sha256((json.dumps(account, sort_keys=True) + KEYWORDS).encode()).hexdigest()


def covers_history(job, account_id, account_fingerprint, start, end):
    """A terminal official-API account search can cover a contained interval."""
    if (job.get('account_id') != account_id or job.get('fingerprint') != account_fingerprint
            or job.get('mode') != 'historical' or job.get('window') != 'account'
            or job.get('status') != 'searched' or job.get('cursor') is not None
            or type(job.get('pages')) is not int or job['pages'] < 1):
        return False
    try:
        target_start = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
        target_end = datetime.fromisoformat(end).replace(tzinfo=timezone.utc)
        source_start = datetime.fromisoformat(job['start']).replace(tzinfo=timezone.utc)
        source_end = datetime.fromisoformat(job['end']).replace(tzinfo=timezone.utc)
        actual_end = datetime.fromisoformat(job['query_end_time'].replace('Z', '+00:00'))
        return (actual_end.tzinfo is not None and source_start <= target_start < target_end <= source_end
                and actual_end >= target_end)
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def current_job(job, fingerprints, config, until=None):
    if (job.get('account_id') not in fingerprints or
            job.get('fingerprint') != fingerprints[job['account_id']]):
        return False
    if job.get('mode') != 'historical':
        return True
    window = config.get('historical_window', 'month')
    if job.get('window', 'month') != window:
        return False
    account = next(a for a in config['accounts'] if a['id'] == job['account_id'])
    start = max(config['since'], account['valid_from'])
    cutoff = job.get('historical_until', config.get('historical_until'))
    ends = [v for v in (cutoff, account.get('valid_until'), until) if v]
    end = min(ends) if ends else None
    # Fixed account intervals must match exactly. Monthly jobs remain bounded
    # subintervals; daily jobs keep their independent overlapping checkpoints.
    if window == 'account':
        return job['start'] == start and (end is None or job['end'] == end)
    return job['start'] >= start and (end is None or job['end'] <= end)
