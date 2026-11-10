"""Offline evidence and research-effort metrics for federal profiles."""
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from federal_x_config import fingerprint, current_job, provider, state_file


def read(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def search_groups(config, subjects, *, require_assignments=True):
    """Expand the exact named queries used by collection and coverage."""
    groups = [{**group, 'queries': list(group['queries']), 'subject_ids': [], 'named_queries': {}}
              for group in config['groups']]
    if not config.get('named_searches'):
        return groups
    by_org = {}
    for group in groups:
        for oid in group['organization_ids']:
            if oid in by_org:
                raise ValueError('Organization assigned to multiple daily groups: ' + oid)
            by_org[oid] = group
    for subject in subjects:
        group = by_org.get(subject['organization_id'])
        if group is not None:
            group['subject_ids'].append(subject['id'])
        elif require_assignments:
            raise ValueError('Federal profile has no daily group: ' + subject['id'])
    names = {subject['id']: subject['name'] for subject in subjects}
    for group in groups:
        for offset in range(0, len(group['subject_ids']), 2):
            ids = group['subject_ids'][offset:offset + 2]
            terms = ' OR '.join('"' + names[pid] + '"' for pid in ids)
            query = f'({terms}) AI artificial intelligence superintelligence policy statements'
            group['queries'].append(query)
            group['named_queries'].setdefault(query, []).extend(ids)
    return groups


def query_key(group, query):
    data = json.dumps([group['id'], query, group['domains']], sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()


def _known_date(value, today):
    try:
        day = date.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return day if value == day.isoformat() and day <= today else None


def _web_freshness(root, subjects, today):
    config = read(root / 'config/federal_sources.json', None)
    state = read(root / 'data/federal_state.json', {})
    queue = state.get('pending')
    pages_by_group = Counter(page.get('group') for page in (queue or {}).values())
    queue_dates = [_known_date(page.get('queued_on'), today) for page in (queue or {}).values()]
    oldest = min((day for day in queue_dates if day is not None), default=None)
    profiles = {}
    query_dates = {}
    named_dates = {}
    for group in search_groups(config or {'groups': []}, subjects, require_assignments=False):
        for query in group['queries']:
            key = query_key(group, query)
            checkpoint = state.get('queries', {}).get(key, {})
            day = _known_date(checkpoint.get('since'), today)
            query_dates[key] = day
            ids = group['named_queries'].get(query)
            if ids is None:
                continue
            named_dates[key] = day
            for pid in ids:
                profiles[pid] = {
                    'group': group['id'], 'named_query': query,
                    'last_success_on': day.isoformat() if day else None,
                    'age_days': (today - day).days if day else None,
                    'pending_named_queries': int(day != today),
                    'group_pending_pages': pages_by_group[group['id']] if queue is not None else None,
                }
    latest = max((day for day in query_dates.values() if day is not None), default=None)
    latest_named = max((day for day in named_dates.values() if day is not None), default=None)
    return profiles, {
        'last_success_on': latest.isoformat() if latest else None,
        'last_named_success_on': latest_named.isoformat() if latest_named else None,
        'configured_named_queries': len(named_dates) if config is not None else None,
        'pending_named_queries': sum(day != today for day in named_dates.values()) if config is not None else None,
        'pending_pages': len(queue) if queue is not None else None,
        'pending_pages_without_queue_date': queue_dates.count(None) if queue is not None else None,
        'oldest_known_pending_on': oldest.isoformat() if oldest else None,
        'oldest_known_pending_age_days': (today - oldest).days if oldest else None,
    }


def _daily_x_freshness(jobs, x_provider, until, queue_known, accounts_due):
    daily_jobs = [job for job in jobs if job['mode'] == 'daily']
    limit = datetime.fromisoformat(until).replace(tzinfo=timezone.utc)
    cutoffs = []
    for job in daily_jobs:
        if job['status'] != 'searched':
            continue
        # The API clamps its actual cutoff. The nominal end is not a substitute.
        value = job.get('query_end_time') if x_provider == 'x_api' else job.get('end', '') + 'T00:00:00Z'
        try:
            cutoff = datetime.fromisoformat(value)
        except (TypeError, ValueError):
            continue
        if cutoff.tzinfo is not None and cutoff <= limit:
            cutoffs.append(cutoff.astimezone(timezone.utc))
    latest = max(cutoffs, default=None)
    return {
        'last_successful_cutoff': latest.isoformat().replace('+00:00', 'Z') if latest else None,
        'pending_windows': sum(job['status'] != 'searched' for job in daily_jobs) if queue_known else None,
        'accounts_due_for_daily_check': accounts_due,
    }


def _daily_x_accounts_due(accounts, jobs, today, until):
    # The daily collector uses tomorrow as the exclusive end for today's job.
    # A new account can be due before the collector persists a job for it.
    checked = {job['account_id'] for job in jobs
               if job['mode'] == 'daily' and job['status'] == 'searched' and job.get('end') == until}
    return [account for account in accounts if account['id'] not in checked
            and account['valid_from'] <= today < (account.get('valid_until') or until)]


def coverage(root, subjects, audit):
    today = datetime.now(timezone.utc).date()
    until = (today + timedelta(days=1)).isoformat()
    web_profiles, web_daily = _web_freshness(root, subjects, today)
    profiles = {}
    source_urls = set()
    x_config=read(root / 'config/federal_x.json', {'accounts':[]})
    x_provider=provider(x_config)
    x_state=read(root / 'data' / state_file(x_config), {})
    x_status=read(root / 'data/federal_x_status.json', {'status':'not_started'})
    if x_status.get('provider','emusks') != x_provider:
        x_status={'status':'not_started','provider':x_provider}
    else:
        x_status={**x_status,'provider':x_provider}
    subject_ids={s['id'] for s in subjects}
    x_accounts=[a for a in x_config['accounts'] if a['subject_id'] in subject_ids]
    account_ids={a['id'] for a in x_accounts}
    fingerprints = {account['id']: fingerprint(account) for account in x_accounts}
    current_jobs = [job for job in x_state.get('jobs', {}).values() if current_job(job, fingerprints, x_config, until)]
    x_enabled = bool(x_config.get('enabled'))
    due_accounts = _daily_x_accounts_due(x_accounts, current_jobs, today.isoformat(), until) if x_enabled else []
    due_by_profile = Counter(account['subject_id'] for account in due_accounts)
    accounts_by_profile = defaultdict(list)
    jobs_by_profile = defaultdict(list)
    account_profiles = {account['id']: account['subject_id'] for account in x_accounts}
    for account in x_accounts:
        accounts_by_profile[account['subject_id']].append(account)
    for job in current_jobs:
        jobs_by_profile[account_profiles[job['account_id']]].append(job)
    x_status={**x_status,'accounts':len({a['handle'].lower() for a in x_accounts}),
        'account_intervals':len(x_accounts),'mapped_profiles':len({a['subject_id'] for a in x_accounts}),
        'unmapped_profiles':len(subject_ids-{a['subject_id'] for a in x_accounts})}
    if 'added' in x_status:
        x_status['added']={pid:ids for pid,ids in x_status['added'].items() if pid in subject_ids}
    if 'errors' in x_status:
        x_status['errors']=[e for e in x_status['errors'] if e.get('account_id') in account_ids or not e.get('account_id')]
    if 'pending_windows' in x_status:
        x_status['pending_windows']=sum(j['status']!='searched' for j in current_jobs if j['mode']==x_status.get('mode'))
    seed_audit = read(root / 'data/federal_seed_research.json', {}).get('profiles', {})
    for subject in subjects:
        statements = read(root / 'evidence' / f"{subject['id']}.json", {'statements': []})['statements']
        statements = [s for s in statements if s.get('verified') is True and s.get('url') and s.get('text')]
        source_urls.update(s['url'] for s in statements)
        passes = audit.get('profiles', {}).get(subject['id'], {}).get('passes', {})
        completed = [p for p in passes.values() if p.get('status') == 'completed']
        dates = sorted(s['date'] for s in statements if s.get('date'))
        profiles[subject['id']] = {
            'name': subject['name'], 'entity_type': subject['entity_type'], 'organization_id': subject['organization_id'],
            'statements': len(statements), 'sources': len({s['url'] for s in statements}),
            'earliest_date': dates[0] if dates else None, 'latest_date': dates[-1] if dates else None,
            'research_status': ('needs_retry' if any(p.get('status') == 'needs_retry' for p in passes.values()) else
                                'searched' if len(completed) >= 8 else 'in_progress' if completed else 'not_started'),
            'completed_passes': len(completed), 'search_requests': sum(p.get('searches') or 0 for p in completed),
            'gaps': list(dict.fromkeys(g for p in completed for g in p.get('gaps', []))),
            'rejected_excerpts': sum(p.get('rejected', 0) for p in completed),
            'official_leads_checked': seed_audit.get(subject['id'], {}).get('sources_checked', 0),
            'official_leads_pending': seed_audit.get(subject['id'], {}).get('sources_pending', 0),
        }
        pid = subject['id']
        accounts = accounts_by_profile[pid]
        jobs = jobs_by_profile[pid]
        profiles[pid]['daily'] = {
            'web': web_profiles.get(pid, {
                'group': None, 'named_query': None, 'last_success_on': None, 'age_days': None,
                'pending_named_queries': None, 'group_pending_pages': None,
            }),
            'x': _daily_x_freshness(jobs, x_provider, until, bool(accounts) and 'jobs' in x_state,
                                    due_by_profile[pid] if x_enabled and accounts else None),
        }
        profiles[subject['id']].update(
            x_accounts=len({a['handle'].lower() for a in accounts}),x_account_intervals=len(accounts),
            x_statements=sum(s.get('origin')=='federal_x' for s in statements),
            x_windows_searched=sum(j['status']=='searched' for j in jobs),
            x_status=('unmapped' if not accounts else 'unavailable' if x_status['status']=='unavailable' else
                      'partial' if any(j['status']!='searched' for j in jobs) else 'searched' if jobs else 'not_started'))
    people = [p for p in profiles.values() if p['entity_type'] == 'person']
    counts = [p['statements'] for p in people]
    congress = read(root / 'data/roster.json', [])
    cc = [len(read(root / 'evidence' / f"{p['id']}.json", {'statements': []})['statements']) for p in congress]
    daily = {
        'web': web_daily,
        'x': _daily_x_freshness(current_jobs, x_provider, until, 'jobs' in x_state,
                                len(due_accounts) if x_enabled else None),
        'note': 'The daily schedule queues searches. Collection limits can leave profiles pending across days.',
    }
    return {'updated_on': today.isoformat(), 'profiles': profiles, 'x':x_status, 'daily': daily, 'summary': {
        'people': len(people), 'institutions': len(profiles) - len(people),
        'statements': sum(p['statements'] for p in profiles.values()),
        'unique_source_pages': len(source_urls),
        'official_source_pages_checked': len({url for pid,p in seed_audit.items() if pid in subject_ids for url, entry in p.get('sources', {}).items() if entry.get('status') == 'completed'}),
        'people_median_statements': statistics.median(counts) if counts else 0,
        'people_without_evidence': sum(n == 0 for n in counts), 'people_with_12_statements': sum(n >= 12 for n in counts),
        'people_searched': sum(p['completed_passes'] > 0 for p in people),
        'people_completed': sum(p['completed_passes'] >= 8 for p in people),
        'congress_people': len(cc), 'congress_median_statements': statistics.median(cc) if cc else 0,
        'congress_statements': sum(cc),
        'x_accounts':len({a['handle'].lower() for a in x_accounts}), 'x_account_intervals':len(x_accounts),
        'x_mapped_profiles':len({a['subject_id'] for a in x_accounts}),
        'x_statements':sum(p['x_statements'] for p in profiles.values()),
    }}
