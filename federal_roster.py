"""Sourced office inventory and bounded directory checks; never changes eligibility."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

import policy_subjects

INVENTORY = 'config/federal_roster_inventory.json'
CHECKS = 'data/federal_role_checks.json'
STATES = ('included', 'candidate', 'unresolved', 'vacant', 'not_public', 'out_of_scope', 'not_selected')


def _read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def _url(value):
    try:
        parts = urlsplit(value)
        return parts.scheme == 'https' and bool(parts.hostname) and not parts.username and not parts.password
    except (ValueError, TypeError):
        return False


def load_inventory(root: Path) -> dict:
    root = Path(root)
    inventory = _read(root / INVENTORY)
    if inventory is None:
        return {}
    if inventory.get('version') != 1:
        raise ValueError('Invalid roster inventory version')
    date.fromisoformat(inventory['checked_on'])
    organizations = {o['id']: o for o in inventory['organizations']}
    if len(organizations) != len(inventory['organizations']):
        raise ValueError('Duplicate inventory organization')
    registry = policy_subjects.load_registry(root)
    known = {o['id'] for o in registry['organizations']}
    eligible = {p['id'] for p in policy_subjects.load_subjects(root)
                if p['branch'] == 'executive' and p['entity_type'] == 'person'}
    for oid, org in organizations.items():
        if org.get('status') not in ('pending', 'reviewed') or not org.get('name'):
            raise ValueError('Invalid organization review status')
        date.fromisoformat(org['checked_on'])
        if org.get('registry_id') and org['registry_id'] not in known:
            raise ValueError('Unknown registry organization')
        urls = org.get('directory_urls', []) + org.get('reviewed_urls', [])
        if not urls or not all(_url(u) for u in urls):
            raise ValueError('Invalid organization source URL')
        if org['status'] == 'reviewed' and (not org.get('reviewed_urls') or not org.get('notes')):
            raise ValueError('Reviewed organization needs source and review reason')
        seen = {oid}; parent = org.get('parent_id')
        while parent:
            if parent not in organizations or parent in seen:
                raise ValueError('Unknown or cyclic inventory parent')
            seen.add(parent); parent = organizations[parent].get('parent_id')
    seen = set()
    for role in inventory['roles']:
        if (not role.get('id') or role['id'] in seen or role.get('organization_id') not in organizations
                or role.get('status') not in STATES or not role.get('title')
                or role.get('authority_class') not in ('senior_leadership', 'decision_authority')
                or not role.get('authority_reason')):
            raise ValueError('Invalid or duplicate inventory role')
        seen.add(role['id']); date.fromisoformat(role['checked_on'])
        urls = role.get('source_urls', [])
        if not urls or not all(_url(u) for u in urls):
            raise ValueError('Invalid role source URL')
        if role['status'] == 'included' and role.get('subject_id') not in eligible:
            raise ValueError('Included role must reference an eligible current person')
        if role['status'] in ('included', 'vacant', 'not_public', 'out_of_scope', 'not_selected') and not role.get('current_service_evidence'):
            raise ValueError('Role disposition requires positive source evidence')
    return inventory


def coverage_report(root: Path) -> dict:
    root = Path(root); inventory = load_inventory(root)
    if not inventory:
        return {'status': 'unavailable', 'organizations': [], 'summary': {}}
    organizations = {o['id']: o for o in inventory['organizations']}
    roles = inventory['roles']
    checks = _read(root / CHECKS, {}).get('sources', {})
    def descendants(oid):
        result = {oid}
        for child, org in organizations.items():
            if org.get('parent_id') == oid:
                result.update(descendants(child))
        return result
    rows = []
    for oid, org in organizations.items():
        children = descendants(oid)
        rr = [r for r in roles if r['organization_id'] in children]
        counts = Counter(r['status'] for r in rr)
        people = sorted({r['subject_id'] for r in rr if r['status'] == 'included'})
        urls = sorted({u for child in children for u in organizations[child]['directory_urls']})
        source_checks = [checks[u] for u in urls if u in checks]
        rows.append({'id': oid, 'registry_id': org.get('registry_id'), 'name': org['name'],
            'parent_id': org.get('parent_id'), 'status': org['status'], 'checked_on': org['checked_on'],
            'discovery_complete': all(organizations[c]['status'] == 'reviewed' for c in children),
            'included_people': len(people), 'subject_ids': people, 'included_roles': counts['included'],
            'role_counts': dict(counts), 'unresolved_roles': counts['candidate'] + counts['unresolved'],
            'directory_urls': org['directory_urls'], 'notes': org.get('notes', ''),
            'last_directory_check': max((s['checked_on'] for s in source_checks), default=None),
            'pending_role_reviews': sum(bool(s.get('needs_review')) for s in source_checks),
            'unavailable_sources': sum(s.get('status') == 'unavailable' for s in source_checks)})
    counts = Counter(r['status'] for r in roles)
    return {'status': 'available', 'checked_on': inventory['checked_on'], 'organizations': rows,
        'summary': {'organizations': len(rows), 'reviewed_organizations': sum(o['status'] == 'reviewed' for o in rows),
            'included_people': len({r['subject_id'] for r in roles if r['status'] == 'included'}),
            'included_roles': counts['included'], 'candidate_roles': counts['candidate'],
            'unresolved_roles': counts['unresolved'], 'vacant_roles': counts['vacant'],
            'not_public_roles': counts['not_public'], 'out_of_scope_roles': counts['out_of_scope'],
            'not_selected_roles': counts['not_selected'],
            'pending_role_reviews': sum(bool(s.get('needs_review')) for s in checks.values())}}


def _fetch_directory(url):
    import httpx
    from scripts.daily.federal_sources import PageText
    hostname = urlsplit(url).hostname or ''
    if not _url(url) or not hostname.endswith(('.gov', '.mil')):
        raise ValueError('Directory monitoring requires an official government host')
    # Validate every redirect before following it; configuration is not a network allowlist.
    with httpx.Client(timeout=12, follow_redirects=False) as client:
        for _ in range(5):
            response = client.get(url, headers={'User-Agent': 'Federal-public-source-monitor/1.0'})
            if response.is_redirect:
                from urllib.parse import urljoin
                url = urljoin(url, response.headers['location'])
                hostname = urlsplit(url).hostname or ''
                if not _url(url) or not hostname.endswith(('.gov', '.mil')):
                    raise ValueError('Directory redirect leaves official hosts')
                continue
            response.raise_for_status()
            parser = PageText(); parser.feed(response.text)
            text = ' '.join(parser.parts)
            if len(text.strip()) < 80:
                raise ValueError('Directory text unavailable')
            return text
    raise ValueError('Too many directory redirects')


def check_directories(root: Path, *, asof=None, fetch=None, max_pages=40) -> dict:
    root = Path(root); asof = asof or date.today().isoformat()
    day = date.fromisoformat(asof)
    if max_pages < 1:
        raise ValueError('max_pages must be positive')
    inventory = load_inventory(root)
    if not inventory:
        return {'status': 'unavailable', 'checked': 0}
    state = _read(root / CHECKS, {'version': 1, 'sources': {}})
    sources = state['sources']
    urls = {u for o in inventory['organizations'] for u in o['directory_urls']}
    cutoff = (day - timedelta(days=7)).isoformat()
    due = sorted((u for u in urls if sources.get(u, {}).get('checked_on', '') <= cutoff),
                 key=lambda u: (sources.get(u, {}).get('checked_on', ''), u))
    selected = due[:max_pages]
    def check(url):
        previous = sources.get(url, {})
        try:
            text = ' '.join((fetch or _fetch_directory)(url).split())
            digest = hashlib.sha256(text.encode()).hexdigest()
            changed = bool(previous.get('text_hash') and previous['text_hash'] != digest)
            needs_review = previous.get('needs_review', False) or changed
            return url, {**previous, 'checked_on': asof, 'last_success': asof, 'text_hash': digest,
                         'status': 'review_needed' if needs_review else 'unchanged',
                         'needs_review': needs_review, 'baseline_only': not previous.get('text_hash')}
        except Exception as exc:
            return url, {**previous, 'checked_on': asof, 'status': 'unavailable', 'error': type(exc).__name__}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for url, result in pool.map(check, selected):
            sources[url] = result
    state['checked_on'] = asof
    path = root / CHECKS; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + '\n')
    return {'status': 'ok', 'checked': len(selected), 'pending_sources': len(due) - len(selected),
            'review_needed': sum(bool(s.get('needs_review')) for s in sources.values()),
            'unavailable': sum(s.get('status') == 'unavailable' for s in sources.values())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['report', 'check'])
    parser.add_argument('--max-pages', type=int, default=40)
    args = parser.parse_args(); root = Path(__file__).resolve().parent
    result = coverage_report(root) if args.command == 'report' else check_directories(root, max_pages=args.max_pages)
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
