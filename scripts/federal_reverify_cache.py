"""Revalidate cached federal excerpts with no network or model calls."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts'), str(ROOT / 'scripts/daily')]
import federal
import federal_research as research
import federal_sources as sources
import policy_subjects


def reverify_subject(root, subject):
    pid = subject['id']
    directory = root / 'data/raw/federal_research' / pid
    pages = {}
    for path in directory.glob('page-*.json'):
        page = federal.read(path, {})
        if research.public_url(page.get('url')) and page.get('text') and page.get('verified_via'):
            pages[sources.digest(sources.canonical_url(page['url']))] = page
    existing = federal.read(root / f'evidence/{pid}.json', {'statements': []})['statements']
    statements = []
    report = {'checked_on': federal.today(), 'rows_checked': 0, 'rejected': 0,
              'missing_pages': [], 'added_sids': [], 'paid_calls': 0}
    for path in sorted(directory.glob('seed-*.json')):
        source_hash = path.stem.rsplit('-', 1)[0][len('seed-'):]
        page = pages.get(source_hash)
        if page is None:
            report['missing_pages'].append(path.name)
            continue
        rows = federal.read(path, [])
        if not isinstance(rows, list):
            raise ValueError('Invalid cached seed extraction')
        for row in rows:
            report['rows_checked'] += 1
            valid, rejected = federal.validate_rows(page, [research.source_context(row, page, subject)], [subject], federal.today())
            report['rejected'] += rejected
            for _, statement in valid:
                if not research.overlaps(statement, existing + statements):
                    statements.append({**statement, 'origin': 'federal_cached_reverification',
                                       'retrieved_on': page.get('retrieved_on'), 'reverified_on': federal.today()})
    report['added_sids'] = federal.append_evidence(root, pid, statements)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ids', required=True)
    args = parser.parse_args()
    ids = set(args.ids.split(','))
    subjects = {s['id']: s for s in policy_subjects.load_subjects(ROOT) if s['branch'] == 'executive'}
    if not ids or not ids <= set(subjects):
        parser.error('Only current federal profiles can be reverified')
    path = ROOT / 'data/federal_cached_reverification.json'
    audit = federal.read(path, {'version': 1, 'profiles': {}})
    pending = False
    for pid in sorted(ids):
        report = reverify_subject(ROOT, subjects[pid])
        pending = pending or bool(report.get('missing_pages'))
        previous = audit['profiles'].get(pid, {})
        audit['profiles'][pid] = {**report, 'previous_attempts': previous.get('previous_attempts', []) +
            ([{k: v for k, v in previous.items() if k != 'previous_attempts'}] if previous else [])}
        federal.write(path, audit)
        print(json.dumps({'id': pid, **report}), flush=True)
    return 1 if pending else 0


if __name__ == '__main__':
    raise SystemExit(main())
