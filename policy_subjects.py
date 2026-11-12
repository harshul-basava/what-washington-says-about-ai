"""Additional policy subjects; the congressional scoring roster stays unchanged."""
import json
import hashlib
import html
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse, urldefrag

ATTRIBUTION_INSTRUCTIONS = """For evidence with attribution metadata, classify only the named subject's
position in the stated capacity. An institutional statement represents that institution,
not the private views of its leaders or every member. An official-role statement belongs
to the named speaker in that role; do not transfer it to other appointments or institutions.
Joint institutional statements do not prove personal endorsement by individual members.
Role membership and source-page context alone do not establish a policy stance.
Do not infer support for embedded auditors from ordinary security testing or external audits."""


def _read(path):
    return json.loads(Path(path).read_text())


def _url(value):
    parsed = urlparse(value or '')
    return parsed.scheme in ('http', 'https') and bool(parsed.netloc)


def load_registry(root):
    path = Path(root) / 'config/policy_subjects.json'
    return _read(path) if path.exists() else {'version': 1, 'organizations': [], 'subjects': []}


def load_scope(root, registry=None):
    """Explicit current-government eligibility; unreviewed federal profiles stay out."""
    registry = registry if registry is not None else load_registry(root)
    path = Path(root) / 'config/federal_scope.json'
    if not path.exists():
        if registry.get('coverage_mode') == 'current_government':
            raise ValueError('Current government scope file is required')
        return None
    scope = _read(path)
    if scope.get('version') != 1 or scope.get('mode') != 'current_government':
        raise ValueError('Invalid federal scope')
    date.fromisoformat(scope['reviewed_on'])
    known = {p['id'] for p in registry['subjects']}
    seen = set()
    for row in scope['profiles']:
        pid = row.get('subject_id')
        if (pid not in known or pid in seen or row.get('decision') not in ('include', 'exclude')
                or not row.get('reason') or not row.get('checked_on')
                or (row['decision'] == 'include' and not _url(row.get('source_url')))):
            raise ValueError('Invalid or unsourced federal scope entry')
        date.fromisoformat(row['checked_on'])
        seen.add(pid)
    return scope


def load_subjects(root):
    config = load_registry(root)
    scope = load_scope(root, config)
    eligible = ({row['subject_id']: row for row in scope['profiles'] if row['decision'] == 'include'}
                if scope is not None else None)
    organizations = {o['id']: o for o in config['organizations']}
    if config['version'] != 1 or len(organizations) != len(config['organizations']):
        raise ValueError('Invalid subject registry or duplicate organization')
    def ancestry(oid):
        chain = []
        while oid:
            if oid not in organizations or oid in chain:
                raise ValueError('Unknown or cyclic organization parent')
            chain.append(oid)
            oid = organizations[oid].get('parent_id')
        return chain
    for oid in organizations:
        ancestry(oid)
    subjects = [{**p, 'entity_type': 'person', 'branch': 'legislative', 'roles': []}
                for p in _read(Path(root) / 'data/roster.json')]
    seen = {p['id'] for p in subjects}
    for original in config['subjects']:
        p = dict(original)
        if not re.fullmatch(r'[a-z][a-z0-9_]*', p['id']) or p['id'] in seen:
            raise ValueError('Invalid or duplicate subject ID: ' + p['id'])
        seen.add(p['id'])
        if p['entity_type'] not in ('person', 'institution') or p['branch'] != 'executive':
            raise ValueError('Invalid executive subject type')
        if p['organization_id'] not in organizations:
            raise ValueError('Unknown subject organization')
        for role in p['roles']:
            if role['organization_id'] not in organizations or not role.get('title') or not _url(role.get('source_url')):
                raise ValueError('Invalid role reference')
            for key in ('start_date', 'end_date', 'verified_on'):
                if role.get(key):
                    date.fromisoformat(role[key])
            if not role.get('verified_on') or (role.get('start_date') and role.get('end_date') and role['end_date'] < role['start_date']):
                raise ValueError('Invalid role dates')
        p.update(party=None, state='', chamber='', status='institution' if p['entity_type'] == 'institution' else 'official',
                 organization_name=organizations[p['organization_id']]['name'],
                 organization_ids=sorted({ancestor for oid in [p['organization_id'], *[r['organization_id'] for r in p['roles']]] for ancestor in ancestry(oid)}))
        if eligible is not None:
            if p['id'] not in eligible:
                continue
            p['government_scope'] = {k: eligible[p['id']][k] for k in ('checked_on', 'source_url', 'reason')}
        subjects.append(p)
    return subjects


def source_quote_key(statement):
    if not statement.get('url'):
        return None
    return (urldefrag(statement['url'])[0],
            ' '.join(html.unescape(statement['text']).split()).casefold())


def active_evidence(statements):
    """Keep correction records and stable IDs on disk, but exclude proven copies."""
    if not any('duplicate_of' in s for s in statements):
        return statements
    by_id = {s['sid']: s for s in statements}
    for row in statements:
        if 'duplicate_of' not in row:
            continue
        original = by_id.get(row['duplicate_of'])
        if (original is None or original is row or 'duplicate_of' in original
                or source_quote_key(row) is None
                or source_quote_key(row) != source_quote_key(original)):
            raise ValueError('Duplicate correction requires the same source and quotation')
    return [s for s in statements if 'duplicate_of' not in s]


def load_evidence(root, subject):
    statements = _read(Path(root) / 'evidence' / f"{subject['id']}.json")['statements']
    seen = set()
    for s in statements:
        if not re.fullmatch(r's\d+', s['sid']) or s['sid'] in seen:
            raise ValueError('Invalid or duplicate statement ID')
        seen.add(s['sid'])
        if subject['branch'] != 'executive':
            continue
        attr = s.get('attribution', {})
        kind = attr.get('kind')
        if kind not in ('personal', 'official_role', 'institutional') or not attr.get('speaker'):
            raise ValueError('Executive evidence requires explicit attribution')
        if attr['speaker'] != subject['name']:
            raise ValueError('Statement speaker must match the profile owner')
        if (kind == 'institutional') != (subject['entity_type'] == 'institution'):
            raise ValueError('Statement attribution does not match subject type')
        if kind == 'official_role' and (not attr.get('role') or attr.get('organization_id') not in {r['organization_id'] for r in subject['roles']}):
            raise ValueError('Official attribution requires a sourced role')
        if kind == 'institutional' and attr.get('organization_id') != subject['id']:
            raise ValueError('Institutional attribution requires the named institution')
    return active_evidence(statements)


def public_profile(subject):
    fields = ('id', 'name', 'party', 'state', 'chamber', 'status', 'entity_type', 'branch',
              'organization_id', 'organization_ids', 'organization_name', 'roles', 'source_url', 'description', 'aliases', 'verified_on', 'government_scope')
    return {k: subject[k] for k in fields if k in subject}


def public_evidence(statement):
    """Keep copied non-government attribution context in local verification storage only."""
    if not statement.get('attribution') or (urlparse(statement.get('url', '')).hostname or '').endswith(('.gov', '.mil')):
        return statement
    span_hash = statement.get('attribution_span_sha256') or hashlib.sha256(statement.get('context', '').encode()).hexdigest()
    speaker = statement['attribution'].get('speaker', 'the named subject')
    return {**statement, 'attribution_span_sha256': span_hash,
            'context': f'Verified direct statement by {speaker}. Local verification records retain the source attribution.'}
