"""Daily federal evidence collection; separate from congressional score collection."""
import argparse
import json
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from common import ROOT, today
import federal_sources as sources
import policy_subjects


def read(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)


def contains_name(text, subject):
    names = [subject['name'], *subject.get('aliases', [])]
    return any(re.search(r'(?<!\w)' + re.escape(sources.normalize(name)) + r'(?!\w)', text, re.I) for name in names)


def checked_date(value, date_quote, text, now):
    if value is None and not date_quote:
        return None
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}(?:-\d{2}(?:-\d{2})?)?', value):
        raise ValueError('Invalid statement date')
    first = date.fromisoformat(value + {4: '-01-01', 7: '-01', 10: ''}[len(value)])
    if first > date.fromisoformat(now) or not date_quote or sources.normalize(date_quote) not in text:
        raise ValueError('Unverified statement date')
    anchor = sources.normalize(date_quote)
    if re.search(r'(?<!\d)' + re.escape(value) + r'(?![\d-])', anchor):
        return value
    for fmt in ('%B %d, %Y', '%b %d, %Y', '%B %d %Y', '%b %d %Y', '%B %Y', '%b %Y'):
        if '%d' not in fmt and len(value) > 7:
            continue
        try:
            parsed = datetime.strptime(anchor, fmt)
            if parsed.strftime('%Y-%m-%d')[:len(value)] == value:
                return value
        except ValueError:
            pass
    raise ValueError('Date anchor does not support the stated date')


def validate_rows(page, rows, subjects, now):
    """Verify quote presence and a local attribution span, without inferring speaker opinions."""
    by_id = {s['id']: s for s in subjects}
    text = sources.normalize(page['text'])
    accepted, rejected = [], 0
    for row in rows:
        try:
            subject = by_id[row['subject_id']]
            quote = sources.normalize(row['quote'])
            context = sources.normalize(row['attribution_quote'])
            if not 8 <= len(quote.split()) <= 150 or len(context) > 3500:
                raise ValueError('Invalid excerpt length')
            if quote not in context or context not in text or not contains_name(context, subject):
                raise ValueError('Unverified quote or attribution')
            if subject['id'] == 'si_task_force' and re.search(r'\b(?:Justice Department|Department of Justice|DOJ)\b', context, re.I):
                raise ValueError('Do not assign the Justice Department task force to the White House task force')
            kind = row['kind']
            if kind not in ('personal', 'official_role', 'institutional'):
                raise ValueError('Unknown attribution')
            if (kind == 'institutional') != (subject['entity_type'] == 'institution'):
                raise ValueError('Incorrect subject type')
            day = checked_date(row.get('date'), row.get('date_quote'), text, now)
            attr = {'kind': kind, 'speaker': subject['name'], 'organization_id': subject['organization_id'],
                    'note': 'Automated extraction; exact quote and local attribution span matched the retrieved source.'}
            if kind == 'institutional':
                attr['organization_id'] = subject['id']
            if kind == 'official_role':
                index = row.get('role_index')
                if type(index) is not int or not 0 <= index < len(subject['roles']):
                    raise ValueError('Unknown role')
                role = subject['roles'][index]
                if sources.normalize(role['title']).casefold() not in context.casefold():
                    raise ValueError('Role not stated in attribution span')
                if day and len(day) == 10 and ((role.get('start_date') and day < role['start_date']) or
                                              (role.get('end_date') and day > role['end_date'])):
                    raise ValueError('Statement is outside the sourced role dates')
                attr.update(organization_id=role['organization_id'], role=role['title'])
            accepted.append((subject['id'], {
                'text': quote, 'date': day, 'context': context, 'url': page['url'],
                'source_type': 'official_statement' if (sources.urlsplit(page['url']).hostname or '').endswith('.gov') else 'reported_statement',
                'verified': True, 'verified_via': page['verified_via'], 'attribution': attr,
                'retrieved_on': now, 'source_text_sha256': sources.digest(text), 'origin': 'federal',
                'date_quote': row.get('date_quote'),
            }))
        except (ValueError, KeyError, TypeError, AttributeError):
            rejected += 1
    return accepted, rejected


def append_evidence(root, subject_id, statements):
    path = root / 'evidence' / f'{subject_id}.json'
    evidence = read(path, None)
    if evidence is None:
        raise ValueError('Federal subject needs an existing evidence file')
    existing = evidence['statements']
    # A release repeated on an index/mirror is one dated quote, even with a different URL.
    # Different dates remain distinct; preserve the first source and all published IDs.
    known = {(sources.normalize(s['text']), s.get('date')) for s in existing}
    next_id = max((int(s['sid'][1:]) for s in existing), default=0) + 1
    added = []
    for statement in statements:
        key = (sources.normalize(statement['text']), statement.get('date'))
        if key in known:
            continue
        known.add(key)
        sid = f's{next_id}'; next_id += 1
        existing.append({**statement, 'sid': sid, 'added': today()})
        added.append(sid)
    if added:
        write(path, evidence)
    return added


def collect(root, config, since=None, dry=False):
    root = Path(root)
    subjects = [s for s in policy_subjects.load_subjects(root) if s['branch'] == 'executive']
    state_path = root / 'data/federal_state.json'
    state = read(state_path, {'groups': {}, 'pending': {}, 'processed': {}})
    now = today()
    report = {'date': now, 'status': 'dry_run' if dry else 'ok', 'groups': {}, 'added': {}, 'errors': [],
              'pending_pages': len(state['pending']), 'pages_per_group': config['pages_per_group']}
    if since:
        date.fromisoformat(since)
    for group in config['groups']:
        previous = state['groups'].get(group['id'], {}).get('since')
        start = since or ((date.fromisoformat(previous) - timedelta(days=config['overlap_days'])).isoformat() if previous
                          else (date.fromisoformat(now) - timedelta(days=config['bootstrap_days'])).isoformat())
        report['groups'][group['id']] = {'since': start, 'searches': len(group['queries']), 'pages_checked': 0, 'rejected': 0}
    if dry:
        return report
    try:
        client = sources.Client(root, config['collection_max_cost'])
    except Exception as exc:
        report.update(status='partial', errors=[{'stage': 'setup', 'error': type(exc).__name__}])
        return report
    in_memory = {}
    extraction_revision = sources.digest(sources.EXTRACTION_PROMPT + json.dumps(subjects, sort_keys=True))
    all_domains = sorted({d for g in config['groups'] for d in g['domains']})
    for group in config['groups']:
        gid = group['id']; info = report['groups'][gid]
        ok = True
        pages = [{'url': u, 'title': '', 'publishedDate': None} for u in group['watch_urls']]
        for number, query in enumerate(group['queries'], 1):
            print(f"federal {gid}: search {number}/{len(group['queries'])}", flush=True)
            try:
                pages.extend(client.search(query, group['domains'], info['since']))
            except Exception as exc:
                ok = False
                report['errors'].append({'group': gid, 'stage': 'search', 'error': type(exc).__name__})
        for page in pages:
            if not sources.allowed_url(page.get('url'), group['domains']):
                continue
            page = {**page, 'url': sources.canonical_url(page['url'])}
            url = page['url']
            discovery_hash = sources.digest(sources.normalize(page.get('text') or ''))
            processed = state['processed'].get(url, {})
            recent = processed.get('retrieved_on', '0001-01-01') > (date.fromisoformat(now) - timedelta(days=7)).isoformat()
            if (url not in group['watch_urls'] and recent and processed.get('extraction_revision') == extraction_revision
                    and processed.get('discovery_hash') == discovery_hash and url not in state['pending']):
                continue
            if len(page.get('text') or '') > len(in_memory.get(url, {}).get('text') or '') or url not in in_memory:
                in_memory[url] = page
            state['pending'].setdefault(url, {k: page.get(k) for k in ('url', 'title', 'publishedDate')})
            state['pending'][url].setdefault('group', gid)
            state['pending'][url]['discovery_hash'] = discovery_hash
        if ok:
            state['groups'][gid] = {'since': now}
        # Persist discovery before extracting; never save full source pages in the public repository.
        write(state_path, state)
    checked = Counter()
    for url, queued in list(state['pending'].items()):
        gid = queued['group']
        if gid not in report['groups'] or checked[gid] >= config['pages_per_group']:
            continue
        checked[gid] += 1
        print(f'federal {gid}: check page {checked[gid]}/{config["pages_per_group"]}', flush=True)
        try:
            page = client.page(in_memory.get(url, queued), all_domains)
            page['verified_via'] = page.get('verified_via', 'exact_normalized_search_retrieval')
            content_hash = sources.digest(sources.normalize(page['text']))
            revision = sources.digest(content_hash + extraction_revision)
            if state['processed'].get(url, {}).get('revision') != revision:
                text = sources.normalize(page['text'])
                # Overlap chunks so an excerpt at a boundary remains available in full.
                cursor = queued.get('next_chunk', 0) if queued.get('revision') == revision else 0
                for index, start in enumerate(range(0, len(text), 22000)):
                    if index < cursor:
                        continue
                    chunk = {**page, 'text': text[start:start + 26000]}
                    rows = client.extract(chunk, subjects)
                    valid, invalid = validate_rows(chunk, rows, subjects, now)
                    for pid in sorted({pid for pid, _ in valid}):
                        added = append_evidence(root, pid, [{**s, 'source_text_sha256': content_hash} for who, s in valid if who == pid])
                        if added:
                            report['added'].setdefault(pid, []).extend(added)
                    report['groups'][gid]['rejected'] += invalid
                    if invalid:
                        raise ValueError('Unverified extraction rows; page remains pending')
                    queued.update(revision=revision, next_chunk=index + 1)
                    write(state_path, state)
                state['processed'][url] = {'revision': revision, 'source_text_sha256': content_hash,
                                           'retrieved_on': now, 'verified_via': page['verified_via'],
                                           'extraction_revision': extraction_revision, 'discovery_hash': queued.get('discovery_hash')}
            else:
                state['processed'][url].update(retrieved_on=now, discovery_hash=queued.get('discovery_hash'))
            del state['pending'][url]
            report['groups'][gid]['pages_checked'] += 1
        except Exception as exc:
            report['errors'].append({'group': gid, 'stage': 'page', 'url': url, 'error': type(exc).__name__})
            # Move failures behind the remaining backlog so one blocked page cannot starve a group.
            state['pending'][url] = state['pending'].pop(url)
        write(state_path, state)
    report['pending_pages'] = len(state['pending'])
    if report['errors'] or report['pending_pages']:
        report['status'] = 'partial'
    return report


def judge(root, max_cost, dry=False):
    import policy_cascade as cascade
    import phase3_policies as runner
    p = runner.p
    registry = p.load_registry(root)
    items = runner.select_scope(p.candidates(root, registry), policy_subjects.load_subjects(root), 'executive')
    rubric = (root / 'config/policy_rubric.md').read_text()
    confidence = (root / 'config/policy_confidence.md').read_text()
    strategy = cascade.load_strategy(root)
    saved = read(root / 'data/policy_cascade.json', {'schema_version': 1, 'results': {}})
    errors = 0
    work = [job for role in cascade.ROLES for job in cascade.jobs(items, saved, registry, rubric, confidence, strategy, role, 1)]
    if work and not dry:
        args = SimpleNamespace(max_cost=max_cost, workers=1, batch_size=1, daily=True)
        errors = runner.label_cascade(items, saved, registry, rubric, confidence, strategy, args)
    counts = Counter(cascade.resolve(s, target, saved, registry, rubric, confidence, strategy)['review_status']
                     for s in items for target in s['targets'])
    pending = counts['awaiting_deepseek'] + counts['awaiting_astra']
    return {'status': 'dry_run' if dry else ('partial' if errors or pending else 'ok'),
            'candidate_statements': len(items), 'pending_pairs': pending, 'incomplete_batches': errors,
            'review_counts': dict(counts)}


def build(root):
    import policy_judgments
    return policy_judgments.build(root)


def run(root, config, since=None, dry=False, skip_collect=False):
    report = {'date': today(), 'status': 'dry_run' if dry else 'ok', 'schedule_utc': '11:00'}
    if not dry:
        write(root / 'data/federal_status.json', {**report, 'status': 'in_progress'})
    for stage, action in [('collection', lambda: collect(root, config, since, dry)),
                          ('judgments', lambda: judge(root, config['judgment_max_cost'], dry))]:
        if stage == 'collection' and skip_collect:
            report[stage] = {'status': 'skipped'}
            continue
        try:
            report[stage] = action()
        except Exception as exc:
            report[stage] = {'status': 'partial', 'error': type(exc).__name__}
        if report[stage]['status'] == 'partial':
            report['status'] = 'partial'
        if not dry:
            write(root / 'data/federal_status.json', {**report, 'status': 'in_progress', 'last_completed_stage': stage})
    if not dry:
        import llm
        report['spend_month'] = round(llm.spent_this_month('openrouter'), 4)
        write(root / 'data/federal_status.json', report)
        try:
            build(root)
        except Exception as exc:
            report.update(status='partial', build_error=type(exc).__name__)
            write(root / 'data/federal_status.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--since', help='Search start date, YYYY-MM-DD')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--skip-collect', action='store_true')
    args = parser.parse_args(argv)
    config = read(ROOT / 'config/federal_sources.json', None)
    report = run(ROOT, config, args.since, args.dry_run, args.skip_collect)
    print(json.dumps(report, indent=2), flush=True)
    return report


if __name__ == '__main__':
    result = main()
    if result['status'] == 'partial':
        sys.exit(1)
