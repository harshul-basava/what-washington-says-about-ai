"""Additional policy subjects; the congressional scoring roster stays unchanged."""
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

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


def load_subjects(root):
    config = load_registry(root)
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
        subjects.append(p)
    return subjects


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
    return statements


def public_profile(subject):
    fields = ('id', 'name', 'party', 'state', 'chamber', 'status', 'entity_type', 'branch',
              'organization_id', 'organization_ids', 'organization_name', 'roles', 'source_url', 'description', 'aliases', 'verified_on')
    return {k: subject[k] for k in fields if k in subject}
