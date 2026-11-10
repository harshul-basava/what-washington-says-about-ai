"""Daily federal evidence collection; separate from congressional score collection."""
import argparse
import json
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from common import ROOT, today
import federal_sources as sources
import policy_subjects

public_statement = policy_subjects.public_evidence


def read(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)


def contains_name(text, subject):
    names = [subject['name'], *subject.get('aliases', [])]
    return any(re.search(name_pattern(name), text, re.I) for name in names)


def name_pattern(name):
    parts = sources.normalize(name).split()
    pattern = re.escape(' '.join(parts))
    if len(parts) == 2:
        pattern = re.escape(parts[0]) + r'(?: [A-Z]\.)? ' + re.escape(parts[1])
    return r'(?<!\w)' + pattern + r'(?!\w)'


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
    # A source label is part of the exact anchor, but not of the calendar date.
    anchor = re.sub(r'^(?:(?:Publication Date|Date Published|Release Date|Press Release|FOR IMMEDIATE RELEASE)\s*[:|]\s*|Released\s+)', '', anchor, flags=re.I)
    anchor = re.sub(r'^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+', '', anchor, flags=re.I)
    anchor = re.sub(r'\b(Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.(?=\s)', r'\1', anchor, flags=re.I)
    anchor = re.sub(r'\bSept\.?(?=\s)', 'Sep', anchor, flags=re.I)
    for fmt in ('%B %d, %Y', '%b %d, %Y', '%B %d %Y', '%b %d %Y', '%d %B %Y', '%d %b %Y', '%B %Y', '%b %Y', '%Y %B', '%Y %b'):
        if '%d' not in fmt and len(value) > 7:
            continue
        try:
            parsed = datetime.strptime(anchor, fmt)
            if parsed.strftime('%Y-%m-%d')[:len(value)] == value:
                return value
        except ValueError:
            pass
    raise ValueError('Date anchor does not support the stated date')


def exact_date_anchor(anchor, text):
    """Recover a zero-padded source day without changing date precision or meaning."""
    if not isinstance(anchor, str) or sources.normalize(anchor) in text:
        return anchor
    pattern = re.escape(sources.normalize(anchor))
    pattern = re.sub(r'(?<!\d)([1-9])(?!\d)', r'0?\1', pattern)
    match = re.search(pattern, text)
    return match.group(0) if match else anchor


def explicit_document_author(context, subject):
    """Bind a short authorship header to this person, without crossing recipient fields."""
    if len(context) > 800:
        return False
    who = '(?:' + '|'.join(name_pattern(n) for n in [subject['name'], *subject.get('aliases', [])]) + ')'
    titles = {'President', 'Vice President', 'Secretary', 'Deputy Secretary', 'Under Secretary',
              'Assistant Secretary', 'Principal Deputy Assistant Secretary', 'Secretary of War',
              'Secretary of Defense', 'Director', 'Deputy Director', 'Administrator', 'Chair',
              'Chairman', 'Chairwoman', 'Commissioner', 'Chief Data & AI Officer (CDAO)'}
    for role in subject.get('roles', []):
        titles.update((role['title'], role['title'].split(',')[0]))
    role_pattern = '(?:' + '|'.join(re.escape(sources.normalize(t)) for t in sorted(titles, key=len, reverse=True)) + ')'
    agencies = {subject.get('organization_id', '').replace('_', ' '),
                subject.get('organization_name', '').split('(')[0].strip(), 'U.S.', 'US', 'DoD'} - {''}
    agency_pattern = '(?:' + '|'.join(re.escape(a) for a in sorted(agencies, key=len, reverse=True)) + ')'
    honorific = r'(?:(?:Dr|Mr|Ms|Mrs)\.?\s+|The Honorable\s+|(?:Lieutenant |Major |Brigadier )?General\s+|(?:Vice |Rear )?Admiral\s+){0,2}'
    title = r'(?:(?:U\.S\.|US)\s+)?(?:' + agency_pattern + r'\s+)?' + role_pattern
    author = honorific + '(?:' + title + r'\s+)?' + honorific + who
    if re.search(r'^Office of ' + author + r'\s+(?:Keynote Address|Prepared Remarks|Remarks)\b', context, re.I):
        return True
    markers = r'(?:remarks (?:as prepared for delivery )?(?:by|of)|statement (?:of|by)|testimony (?:of|by)|speech by|prepared (?:remarks|testimony) (?:of|by)|statement for the record|as delivered by|prepared by:|from:)'
    if re.search(r'\b' + markers + r'\s+' + author, context, re.I):
        return True
    header = re.sub(r'^(?:[A-Z][a-z]+ \d{1,2}, \d{4}|\d{4}-\d{2}-\d{2})\s+', '', context)
    # Government releases also use "TITLE NAME Statement on TOPIC" headings.
    if re.search(r'^' + author + r'\s*[,.:–-]?\s+(?:statement|remarks|testimony)\s+(?:on|regarding|before|to|at|for)\b', header, re.I):
        return True
    # After a leading name, permit only a known title before the speech/testimony marker.
    return bool(re.search(r'^' + honorific + who + r'\s*[,.:–-]?\s*(?:' + title +
                          r'\s*[,.:–-]?\s*)?(?:delivers remarks|testimony before|statement before)\b', header, re.I))


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
            basis = row.get('attribution_basis', 'local_span')
            author = (basis == 'document_author' and subject['entity_type'] == 'person'
                      and (sources.urlsplit(page['url']).hostname or '').endswith(('.gov', '.mil'))
                      and context in text[:6000]
                      and (explicit_document_author(context, subject)
                           or (context in text[:1200] and '-Wstate-' in page['url'])
                           or (context in text[:1200] and '/DCPD-' in page['url'] and 'Administration of ' in context and 'The President.' in text[:1200])))
            if (quote not in text or context not in text or not contains_name(context, subject)
                    or (basis == 'document_author' and not author)
                    or (basis == 'local_span' and quote not in context)
                    or basis not in ('local_span', 'document_author')):
                raise ValueError('Unverified quote or attribution')
            if subject['id'] == 'si_task_force' and re.search(r'\b(?:Justice Department|Department of Justice|DOJ)\b', context, re.I):
                raise ValueError('Do not assign the Justice Department task force to the White House task force')
            kind = row['kind']
            if kind not in ('personal', 'official_role', 'institutional'):
                raise ValueError('Unknown attribution')
            if (kind == 'institutional') != (subject['entity_type'] == 'institution'):
                raise ValueError('Incorrect subject type')
            date_anchor = exact_date_anchor(row.get('date_quote'), text)
            day = checked_date(row.get('date'), date_anchor, text, now)
            attr = {'kind': kind, 'speaker': subject['name'], 'organization_id': subject['organization_id'],
                    'basis': basis, 'note': 'Automated extraction; exact quote and attribution span matched the retrieved source.'}
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
            accepted.append((subject['id'], public_statement({
                'text': quote, 'date': day, 'context': context, 'url': page['url'],
                'source_type': 'official_statement' if (sources.urlsplit(page['url']).hostname or '').endswith(('.gov', '.mil')) else 'reported_statement',
                'verified': True, 'verified_via': page['verified_via'], 'attribution': attr,
                'retrieved_on': now, 'source_text_sha256': sources.digest(text), 'origin': 'federal',
                'date_quote': date_anchor,
            })))
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
    reported_urls = {sources.canonical_url(s['url']) for s in statements if not (sources.urlsplit(s['url']).hostname or '').endswith(('.gov', '.mil'))}
    used_words = Counter()
    if reported_urls:
        ids = {p['id'] for p in policy_subjects.load_registry(root)['subjects']} | {subject_id}
        for pid in ids:
            for s in read(root / 'evidence' / f'{pid}.json', {'statements': []})['statements']:
                url = sources.canonical_url(s['url'])
                if url in reported_urls:
                    used_words[url] += len(s['text'].split())
    next_id = max((int(s['sid'][1:]) for s in existing), default=0) + 1
    added = []
    for statement in statements:
        key = (sources.normalize(statement['text']), statement.get('date'))
        if key in known:
            continue
        url = sources.canonical_url(statement['url'])
        if url in reported_urls:
            words = len(statement['text'].split())
            if used_words[url] + words > 25:
                continue
            used_words[url] += words
        known.add(key)
        sid = f's{next_id}'; next_id += 1
        existing.append({**public_statement(statement), 'sid': sid, 'added': today()})
        added.append(sid)
    if added:
        write(path, evidence)
    return added


def search_groups(config, subjects):
    """Expand agency assignments into named searches for the eligible federal roster."""
    groups = [{**g, 'queries': list(g['queries']), 'subject_ids': []} for g in config['groups']]
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
        if not group:
            raise ValueError('Federal profile has no daily group: ' + subject['id'])
        group['subject_ids'].append(subject['id'])
    by_id = {s['id']: s for s in subjects}
    for group in groups:
        for offset in range(0, len(group['subject_ids']), 2):
            names = [by_id[sid]['name'] for sid in group['subject_ids'][offset:offset + 2]]
            group['queries'].append('(' + ' OR '.join('"' + n + '"' for n in names) + ') AI artificial intelligence superintelligence policy statements')
    return groups


def fair_groups(groups, state):
    return sorted(groups, key=lambda g: state.get('groups', {}).get(g['id'], {}).get('since', '0001-01-01'))


def collect(root, config, since=None, dry=False):
    root = Path(root)
    subjects = [s for s in policy_subjects.load_subjects(root) if s['branch'] == 'executive']
    state_path = root / 'data/federal_state.json'
    state = read(state_path, {'groups': {}, 'pending': {}, 'processed': {}})
    state.setdefault('queries', {})
    groups = fair_groups(search_groups(config, subjects), state)
    now = today()
    report = {'date': now, 'status': 'dry_run' if dry else 'ok', 'groups': {}, 'added': {}, 'errors': [],
              'pending_pages': len(state['pending']), 'pages_per_group': config['pages_per_group']}
    if since:
        date.fromisoformat(since)
    for group in groups:
        previous = state['groups'].get(group['id'], {}).get('since')
        start = since or ((date.fromisoformat(previous) - timedelta(days=config['overlap_days'])).isoformat() if previous
                          else (date.fromisoformat(now) - timedelta(days=config['bootstrap_days'])).isoformat())
        report['groups'][group['id']] = {'since': start, 'searches': len(group['queries']), 'subject_ids': group['subject_ids'], 'pages_checked': 0, 'rejected': 0}
    if dry:
        return report
    try:
        client = sources.Client(root, config['collection_max_cost'])
    except Exception as exc:
        report.update(status='partial', errors=[{'stage': 'setup', 'error': type(exc).__name__}])
        return report
    in_memory = {}
    extraction_revision = sources.digest(sources.EXTRACTION_PROMPT + json.dumps(subjects, sort_keys=True))
    all_domains = sorted({d for g in groups for d in g['domains']})
    def enqueue(pages, group):
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
            state['pending'][url].setdefault('group', group['id'])
            state['pending'][url]['discovery_hash'] = discovery_hash
    for group in groups:
        gid = group['id']; info = report['groups'][gid]
        ok = True
        enqueue([{'url': u, 'title': '', 'publishedDate': None} for u in group['watch_urls']], group)
        def query_key(query):
            return sources.digest(json.dumps([gid, query, group['domains']], sort_keys=True))
        queries = sorted(group['queries'], key=lambda q: state['queries'].get(query_key(q), {}).get('since', '0001-01-01'))
        requests = []
        for number, query in enumerate(queries, 1):
            key = query_key(query)
            previous_query = state['queries'].get(key, {}).get('since')
            if previous_query == now and not since:
                continue
            query_since = since or ((date.fromisoformat(previous_query) - timedelta(days=config['overlap_days'])).isoformat()
                                   if previous_query else info['since'])
            print(f"federal {gid}: search {number}/{len(group['queries'])}", flush=True)
            requests.append((key, query, query_since))
        # Only retrieval runs concurrently. The coordinator owns queues and checkpoints;
        # Client reserves the cost of all in-flight requests under its shared lock.
        with ThreadPoolExecutor(max_workers=max(1, min(config.get('search_workers', 1), 8))) as executor:
            futures = {executor.submit(client.search, query, group['domains'], start): key
                       for key, query, start in requests}
            for future in as_completed(futures):
                try:
                    enqueue(future.result(), group)
                    state['queries'][futures[future]] = {'group': gid, 'since': now}
                    write(state_path, state)
                except Exception as exc:
                    ok = False
                    report['errors'].append({'group': gid, 'stage': 'search', 'error': type(exc).__name__})
        if ok or all(state['queries'].get(query_key(q), {}).get('since') == now for q in group['queries']):
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
                    chunk = {**page, 'text': text[start:start + 26000], 'document_header': text[:6000]}
                    named = [s for s in subjects if contains_name(chunk['text'], s) or contains_name(text[:6000], s)]
                    rows = client.extract(chunk, named) if named else []
                    valid, invalid = validate_rows(page, rows, named, now)
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


def schedule_policy_jobs(root, queues, assess, baseline, review_jobs):
    """Give each ready role and profile a turn under the daily allowance."""
    import llm
    path = root / 'data/federal_policy_scheduler.json'
    cursor = read(path, {'version': 1, 'next_stage': 'deepseek'})
    preferred = cursor.get('next_stage')
    if preferred not in queues:
        preferred = 'deepseek'

    while any(queues.values()):
        role = preferred if queues[preferred] else ('astra' if preferred == 'deepseek' else 'deepseek')
        queue = queues[role]
        last_profile = cursor.get('last_profile', {}).get(role, '')
        profile = min((item['person_id'] for item in queue.values()), key=lambda pid: (pid <= last_profile, pid))
        items = [(int(item['sid'][1:]), item) for item in queue.values() if item['person_id'] == profile]
        last_batch, end = cursor.get('batch_cursor', {}).get(role, {}).get(profile, [0, 0])
        batch, item = min(items, key=lambda row: (not last_batch < row[0] <= end, row[0]))
        if not last_batch < batch <= end:
            # Fix the end of this round so new arrivals cannot delay wraparound.
            end = max(number for number, _ in items)

        preferred = 'astra' if role == 'deepseek' else 'deepseek'
        cursor['next_stage'] = preferred
        write(path, cursor)
        status = assess((role, [item]))
        if status == 'budget_exceeded' and llm.spent('openrouter') > baseline:
            # Retry the job with the next invocation's full allowance.
            cursor['next_stage'] = role
            write(path, cursor)
            return

        # Count invalid responses and oversized jobs as turns. Keep them pending
        # in the cache and allow other work to use the remaining allowance.
        del queue[item['key']]
        cursor.setdefault('last_profile', {})[role] = profile
        cursor.setdefault('batch_cursor', {}).setdefault(role, {})[profile] = [batch, end]
        write(path, cursor)
        if status == 'ok' and role == 'deepseek':
            for _, [review] in review_jobs([item]):
                existing = queues['astra'].get(review['key'])
                if existing:
                    review = {**review, 'targets': sorted(set(existing['targets']) | set(review['targets']))}
                queues['astra'][review['key']] = review


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
    def jobs(candidates, role):
        return cascade.jobs(candidates, saved, registry, rubric, confidence, strategy, role, 1)

    if not dry and max_cost != 0:
        queues = {role: {item['key']: item for _, [item] in jobs(items, role)} for role in cascade.ROLES}
        if any(queues.values()):
            args = SimpleNamespace(max_cost=max_cost, workers=1, daily=True)
            def schedule(assess, baseline):
                schedule_policy_jobs(root, queues, assess, baseline, lambda batch: jobs(batch, 'astra'))
            errors = runner.label([], saved, registry, rubric, args, strategy, confidence, root=root, schedule=schedule)
    counts = Counter(cascade.resolve(s, target, saved, registry, rubric, confidence, strategy)['review_status']
                     for s in items for target in s['targets'])
    pending = counts['awaiting_deepseek'] + counts['awaiting_astra']
    return {'status': 'dry_run' if dry else ('partial' if errors or pending else 'ok'),
            'candidate_statements': len(items), 'pending_pairs': pending, 'incomplete_batches': errors,
            'review_counts': dict(counts)}


def build(root):
    import policy_judgments
    if (root / 'config/federal_analysis.json').exists():
        import federal_analysis
        federal_analysis.build(root)
    return policy_judgments.build(root)


def run(root, config, since=None, dry=False, skip_collect=False):
    import federal_x
    import llm
    model_start = None
    scheduler_path = root / 'data/federal_judgment_scheduler.json'
    scheduler = read(scheduler_path, {'version': 1, 'next_stage': 'judgments'})
    first = scheduler.get('next_stage', 'judgments')
    if first not in ('judgments', 'analysis'):
        first = 'judgments'
    def remaining_model_allowance():
        return config['judgment_max_cost'] if dry else max(0, config['judgment_max_cost'] - (llm.spent('openrouter') - model_start))
    def broad_analysis():
        if not (root / 'config/federal_analysis.json').exists():
            return {'status': 'not_configured'}
        import federal_analysis_models
        return federal_analysis_models.run(root, max_cost=remaining_model_allowance(), workers=2, daily=True, dry=dry)
    report = {'date': today(), 'status': 'dry_run' if dry else 'ok', 'schedule_utc': '11:00'}
    if not dry:
        write(root / 'data/federal_status.json', {**report, 'status': 'in_progress'})
    judges = {'judgments': lambda: judge(root, remaining_model_allowance(), dry), 'analysis': broad_analysis}
    order = [first, 'analysis' if first == 'judgments' else 'judgments']
    report['judgment_order'] = order
    for stage, action in [('collection', lambda: collect(root, config, since, dry)),
                          ('x', lambda: federal_x.collect(root, since=since, dry=dry)),
                          *[(name, judges[name]) for name in order]]:
        if stage == first and not dry:
            model_start = llm.spent('openrouter')
            # Persist the next turn before a paid request, including failed requests.
            write(scheduler_path, {'version': 1, 'next_stage': order[1]})
        if stage in ('collection', 'x') and skip_collect:
            report[stage] = {'status': 'skipped'}
            continue
        try:
            report[stage] = action()
        except Exception as exc:
            report[stage] = {'status': 'partial', 'error': type(exc).__name__}
        if report[stage]['status'] in ('partial', 'unavailable'):
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
