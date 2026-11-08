"""Offline evidence and research-effort metrics for federal profiles."""
import json
import statistics
from datetime import date


def read(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def coverage(root, subjects, audit):
    profiles = {}
    source_urls = set()
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
    people = [p for p in profiles.values() if p['entity_type'] == 'person']
    counts = [p['statements'] for p in people]
    congress = read(root / 'data/roster.json', [])
    cc = [len(read(root / 'evidence' / f"{p['id']}.json", {'statements': []})['statements']) for p in congress]
    return {'updated_on': date.today().isoformat(), 'profiles': profiles, 'summary': {
        'people': len(people), 'institutions': len(profiles) - len(people),
        'statements': sum(p['statements'] for p in profiles.values()),
        'unique_source_pages': len(source_urls),
        'official_source_pages_checked': len({url for p in seed_audit.values() for url, entry in p.get('sources', {}).items() if entry.get('status') == 'completed'}),
        'people_median_statements': statistics.median(counts) if counts else 0,
        'people_without_evidence': sum(n == 0 for n in counts), 'people_with_12_statements': sum(n >= 12 for n in counts),
        'people_searched': sum(p['completed_passes'] > 0 for p in people),
        'people_completed': sum(p['completed_passes'] >= 8 for p in people),
        'congress_people': len(cc), 'congress_median_statements': statistics.median(cc) if cc else 0,
        'congress_statements': sum(cc),
    }}
