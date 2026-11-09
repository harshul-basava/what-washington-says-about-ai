"""Offline evidence and research-effort metrics for federal profiles."""
import json
import statistics
from datetime import date, datetime, timedelta, timezone
from federal_x_config import fingerprint, current_job, provider, state_file


def read(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def coverage(root, subjects, audit):
    profiles = {}
    source_urls = set()
    x_config=read(root / 'config/federal_x.json', {'accounts':[]})
    x_provider=provider(x_config)
    x_state=read(root / 'data' / state_file(x_config), {'jobs':{}})
    x_status=read(root / 'data/federal_x_status.json', {'status':'not_started'})
    if x_status.get('provider','emusks') != x_provider:
        x_status={'status':'not_started','provider':x_provider}
    else:
        x_status={**x_status,'provider':x_provider}
    subject_ids={s['id'] for s in subjects}
    x_accounts=[a for a in x_config['accounts'] if a['subject_id'] in subject_ids]
    account_ids={a['id'] for a in x_accounts}
    x_status={**x_status,'accounts':len({a['handle'].lower() for a in x_accounts}),
        'account_intervals':len(x_accounts),'mapped_profiles':len({a['subject_id'] for a in x_accounts}),
        'unmapped_profiles':len(subject_ids-{a['subject_id'] for a in x_accounts})}
    if 'added' in x_status:
        x_status['added']={pid:ids for pid,ids in x_status['added'].items() if pid in subject_ids}
    if 'errors' in x_status:
        x_status['errors']=[e for e in x_status['errors'] if e.get('account_id') in account_ids or not e.get('account_id')]
    if 'pending_windows' in x_status:
        fps={a['id']:fingerprint(a) for a in x_accounts}
        until=(datetime.now(timezone.utc).date()+timedelta(days=1)).isoformat()
        x_status['pending_windows']=sum(j['status']!='searched' for j in x_state['jobs'].values()
            if current_job(j,fps,x_config,until) and j['mode']==x_status.get('mode'))
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
        accounts=[a for a in x_accounts if a['subject_id']==subject['id']]
        account_fingerprints={a['id']:fingerprint(a) for a in accounts}
        until=(datetime.now(timezone.utc).date()+timedelta(days=1)).isoformat()
        jobs=[j for j in x_state['jobs'].values() if current_job(j,account_fingerprints,x_config,until)]
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
    return {'updated_on': date.today().isoformat(), 'profiles': profiles, 'x':x_status, 'summary': {
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
