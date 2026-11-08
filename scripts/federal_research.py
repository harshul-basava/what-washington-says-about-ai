"""Resumable, bounded historical research with independently retrieved quote verification."""
import argparse
import ipaddress
import json
import re
import statistics
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts/daily')]
import federal
import federal_sources as sources
import policy_subjects


def public_url(url):
    try:
        host = urlsplit(url).hostname or ''
        if not sources.allowed_url(url, [host]) or '.' not in host or host.endswith(('.local', '.internal', '.localhost')):
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return True
    except (ValueError, TypeError):
        return False


def official_url(url):
    return (urlsplit(url).hostname or '').endswith(('.gov', '.mil'))


def overlaps(statement, existing):
    text = sources.normalize(statement['text']).casefold()
    return any(statement.get('date') == s.get('date') and
               (text in sources.normalize(s['text']).casefold() or sources.normalize(s['text']).casefold() in text)
               for s in existing)


def source_context(row, page, subject):
    """Recover an exact local span when the model copied its attribution punctuation incorrectly."""
    text = sources.normalize(page['text'])
    quote = sources.normalize(row.get('quote', ''))
    at = text.find(quote)
    if not quote or at < 0:
        return row
    names = [subject['name'], *subject.get('aliases', [])]
    spans = []
    for name in names:
        for match in re.finditer(federal.name_pattern(name), text, re.I):
            start, end = min(at, match.start()), max(at + len(quote), match.end())
            if end - start <= 3300:
                spans.append(text[max(0, start - 80):min(len(text), end + 80)])
    if spans and subject['entity_type'] == 'person' and row.get('attribution_basis', 'local_span') == 'local_span':
        return {**row, 'attribution_quote': min(spans, key=len)}
    if (row.get('attribution_basis') == 'document_author' and official_url(page['url'])
            and '/DCPD-' in page['url'] and federal.contains_name(text[:300], subject)):
        return {**row, 'attribution_quote': text[:300]}
    return row


def limit_quotes(statements, used):
    accepted, rejected = [], 0
    for statement in statements:
        url = sources.canonical_url(statement['url'])
        words = len(statement['text'].split())
        if not official_url(url) and used.get(url, 0) + words > 25:
            rejected += 1
            continue
        used[url] = used.get(url, 0) + words
        accepted.append(statement)
    return accepted, rejected


from federal_coverage import coverage


def record_pass(audit, pid, number, entry):
    passes = audit['profiles'].setdefault(pid, {'passes': {}})['passes']
    old = passes.get(str(number), {})
    if 'added_sids' in entry or old.get('added_sids'):
        entry['added_sids'] = list(dict.fromkeys(old.get('added_sids', []) + entry.get('added_sids', [])))
    passes[str(number)] = entry


def seed_one(root, subject, seeds, client):
    """Read curated government leads in full, with checkpoints for every source chunk."""
    directory = root / 'data/raw/federal_research' / subject['id']
    checkpoint = directory / 'seeds.json'
    audit = federal.read(checkpoint, {'sources': {}, 'added_sids': []})
    leads = list(seeds)
    leads.extend({'url': s['url']} for s in federal.read(root / 'evidence' / f"{subject['id']}.json", {'statements': []})['statements'])
    leads.extend({'url': federal.read(p, {})['url']} for p in directory.glob('page-*.json'))
    unique = {sources.canonical_url(s['url']): s for s in leads if public_url(s.get('url'))}
    for seed in unique.values():
        url = seed['url']
        if not public_url(url) or not official_url(url):
            continue
        url = sources.canonical_url(url)
        previous = audit['sources'].get(url, {})
        if previous.get('status') == 'completed':
            continue
        try:
            cache = directory / ('page-' + sources.digest(url) + '.json')
            if cache.exists():
                page = federal.read(cache, {})
            else:
                page = client.page({'url': url, 'title': seed.get('title', '')}, [urlsplit(url).hostname])
                federal.write(cache, page)
            text = sources.normalize(page['text'])
            entry = {**previous, 'status': 'in_progress', 'source_text_sha256': sources.digest(text)}
            for index, start in enumerate(range(0, len(text), 22000)):
                if index < previous.get('next_chunk', 0):
                    continue
                chunk = {**page, 'text': text[start:start + 26000], 'document_header': text[:6000]}
                rows_cache = directory / (f'seed-{sources.digest(url)}-{index}.json')
                if rows_cache.exists():
                    rows = federal.read(rows_cache, [])
                else:
                    rows = client.extract(chunk, [subject], max_tokens=16000)
                    federal.write(rows_cache, rows)
                rows = [source_context(row, page, subject) for row in rows]
                valid, rejected = federal.validate_rows(page, rows, [subject], federal.today())
                existing = federal.read(root / 'evidence' / f"{subject['id']}.json", {})['statements']
                statements = []
                for _, statement in valid:
                    if not overlaps(statement, existing + statements):
                        statements.append({**statement, 'origin': 'federal_historical_seed'})
                added = federal.append_evidence(root, subject['id'], statements)
                audit['added_sids'].extend(added)
                entry.update(next_chunk=index + 1, rejected=entry.get('rejected', 0) + rejected)
                audit['sources'][url] = entry
                federal.write(checkpoint, audit)
            entry.update(status='completed', date=federal.today())
            audit['sources'][url] = entry
        except Exception as exc:
            audit['sources'][url] = {**audit['sources'].get(url, {}), 'status': 'needs_retry', 'error': type(exc).__name__}
        federal.write(checkpoint, audit)
    return {'sources_checked': sum(s.get('status') == 'completed' for s in audit['sources'].values()),
            'sources_pending': sum(s.get('status') != 'completed' for s in audit['sources'].values()),
            'added_sids': audit['added_sids'], 'date': federal.today(), 'sources': audit['sources']}


def research_one(root, subject, seeds, client, config, pass_number, quote_lock, used_words, refresh=False):
    pid = subject['id']
    directory = root / 'data/raw/federal_research' / pid
    raw_path = directory / f'pass-{pass_number}.json'
    prompt = (root / 'config/federal_research_prompt.md').read_text()
    existing = federal.read(root / 'evidence' / f'{pid}.json', {'statements': []})['statements']
    focuses = [
        'Overview of substantive AI policy statements and recent official speeches.',
        'Historical statements in 2023 and 2024; archived government pages and testimony.',
        'Historical statements in 2025; official speeches, interviews and congressional testimony.',
        'Statements in 2026; new AI frameworks, superintelligence, standards and procurement.',
        'AI safety, frontier models, shutdown rules, independent verification organizations and auditors.',
        'AI export controls, advanced chips, chip smuggling, competition and cooperation with China.',
        'Military and intelligence AI, jobs, civil rights, children, energy and infrastructure; earlier career statements.',
        'Retrieve original speeches and testimony from the supplied source leads; fill gaps in the existing excerpts.',
    ]
    payload = {'today': federal.today(), 'subject': subject, 'source_leads': seeds,
               'pass': pass_number, 'existing_excerpts': [{k: s.get(k) for k in ('text', 'date', 'url')} for s in existing],
               'required_search_focus': focuses[(pass_number - 1) % len(focuses)],
               'followup': 'This is one of eight separate search passes. Use the web search now for this focus. Do not repeat existing excerpts.'}
    if raw_path.exists() and not refresh:
        result = federal.read(raw_path, {})
    else:
        tool = {'type': 'openrouter:web_search', 'parameters': {'engine': 'exa',
                'max_results': config['results_per_search'], 'max_uses': 1,
                'max_total_results': config['results_per_search'],
                'max_characters': config['characters_per_result']}}
        result = client.chat([{'role': 'system', 'content': prompt},
                              {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)}],
                             'federal_historical_research', config['max_output_tokens'], [tool])
        federal.write(raw_path, result)  # Save paid results before any parsing or verification.
    message = result['choices'][0]['message']
    try:
        data = sources.parse_json(message.get('content'))
    except (ValueError, TypeError):
        formatted_path = directory / f'formatted-{pass_number}.json'
        formatted = None
        if formatted_path.exists() and not refresh:
            formatted = federal.read(formatted_path, {})
            try:
                sources.parse_json(formatted['choices'][0]['message'].get('content'))
            except (ValueError, KeyError, TypeError):
                formatted = None
        if formatted is None:
            retrieval = [a['url_citation'] for a in message.get('annotations', []) if a.get('url_citation', {}).get('content')]
            if not retrieval:
                raise ValueError('Search returned no usable text; retry required')
            formatted = client.chat([{'role': 'system', 'content': prompt}, {'role': 'user', 'content': json.dumps({
                **payload, 'instruction': 'The search pass is complete. Extract only from these retrieved source pages. Return the required JSON.',
                'retrieved_pages': retrieval}, ensure_ascii=False)}], 'federal_historical_format', config['max_output_tokens'])
            federal.write(formatted_path, formatted)
        message = {**message, 'content': formatted['choices'][0]['message'].get('content')}
        data = sources.parse_json(message.get('content'))
    searches = (result.get('usage', {}).get('server_tool_use_details') or {}).get('web_search_requests')
    pages = {}
    for annotation in message.get('annotations') or []:
        citation = annotation.get('url_citation') or {}
        if public_url(citation.get('url')) and citation.get('content'):
            url = sources.canonical_url(citation['url'])
            if len(citation['content']) > len(pages.get(url, {}).get('text', '')):
                pages[url] = {'url': url, 'text': citation['content'], 'title': citation.get('title', '')}
    if not isinstance(data, dict) or not isinstance(data.get('statements'), list) or not (searches or pages):
        raise ValueError('Research output lacks verified search activity or a statements list')
    fetched, valid, rejected, errors = {}, [], 0, []
    for row in data['statements']:
        url = row.get('url')
        if row.get('subject_id') != pid or not public_url(url):
            rejected += 1
            continue
        url = sources.canonical_url(url)
        if url not in fetched:
            cache = directory / ('page-' + sources.digest(url) + '.json')
            if cache.exists():
                fetched[url] = federal.read(cache, {})
            else:
                try:
                    fetched[url] = client.page(pages.get(url, {'url': url}), [urlsplit(url).hostname])
                    federal.write(cache, fetched[url])
                except Exception as exc:
                    errors.append({'url': url, 'error': type(exc).__name__})
                    fetched[url] = None
        page = fetched[url]
        accepted = []
        if page:
            accepted, _ = federal.validate_rows(page, [source_context(row, page, subject)], [subject], federal.today())
        if not accepted and url in pages:
            retrieved = {**pages[url], 'verified_via': 'exact_normalized_search_retrieval'}
            accepted, _ = federal.validate_rows(retrieved, [source_context(row, retrieved, subject)], [subject], federal.today())
        if not accepted:
            rejected += 1
            continue
        statement = {**accepted[0][1], 'origin': 'federal_historical', 'research_pass': pass_number}
        if not overlaps(statement, existing + valid):
            valid.append(statement)
    with quote_lock:
        valid, copyright_rejected = limit_quotes(valid, used_words)
        added = federal.append_evidence(root, pid, valid)
    audit = {'status': 'needs_retry' if errors else 'completed', 'date': federal.today(), 'model': client.model,
             'prompt_hash': sources.digest(prompt), 'searches': searches, 'cost': result.get('usage', {}).get('cost'),
             'discovered_sources': len(pages), 'checked_sources': len(fetched), 'added_sids': added,
             'rejected': rejected, 'quotation_limit_rejections': copyright_rejected,
             'source_errors': errors, 'gaps': data.get('gaps', []), 'search_summary': data.get('search_summary', '')}
    federal.write(directory / f'audit-{pass_number}.json', audit)
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'research', 'seeds', 'report'])
    parser.add_argument('--ids')
    parser.add_argument('--pass-number', type=int, default=1)
    parser.add_argument('--rounds', type=int, default=1)
    parser.add_argument('--below', type=int)
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--max-cost', type=float, default=75)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--reverify', action='store_true', help='Recheck cached research only, without new search calls')
    args = parser.parse_args()
    subjects = [s for s in policy_subjects.load_subjects(ROOT) if s['branch'] == 'executive']
    config = federal.read(ROOT / 'config/federal_research.json', {})
    audit_path = ROOT / 'data/federal_research.json'
    audit = federal.read(audit_path, {'version': 1, 'profiles': {}})
    report = coverage(ROOT, subjects, audit)
    selected = [s for s in subjects if (not args.ids or s['id'] in args.ids.split(',')) and
                (args.below is None or report['profiles'][s['id']]['statements'] < args.below)]
    if args.command == 'seeds':
        client = sources.Client(ROOT, args.max_cost, daily=False)
        seeds = federal.read(ROOT / 'config/federal_research_seeds.json', {}).get('subjects', {})
        seed_path = ROOT / 'data/federal_seed_research.json'
        seed_audit = federal.read(seed_path, {'profiles': {}})
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            tasks = {executor.submit(seed_one, ROOT, s, seeds.get(s['id'], []), client): s for s in selected}
            for future in as_completed(tasks):
                pid = tasks[future]['id']; entry = future.result()
                seed_audit['profiles'][pid] = entry
                federal.write(seed_path, seed_audit)
                print(f"{pid}: {entry['sources_checked']} official leads checked, {len(entry['added_sids'])} excerpts, {entry['sources_pending']} pending", flush=True)
        report = coverage(ROOT, subjects, audit)
        federal.write(ROOT / 'data/federal_coverage.json', {**report, 'methodology': config})
        print(json.dumps(report['summary'], indent=2))
        if any(p.get('sources_pending') for p in seed_audit['profiles'].values()):
            raise SystemExit(1)
        return
    pass_numbers = list(range(args.pass_number, args.pass_number + args.rounds))
    selected = [s for s in selected if args.refresh or args.reverify or any(audit['profiles'].get(s['id'], {}).get('passes', {}).get(str(n), {}).get('status') != 'completed' for n in pass_numbers)]
    if args.command == 'plan':
        print(json.dumps({'subjects': [s['id'] for s in selected], 'count': len(selected), 'config': config, 'coverage': report['summary']}, indent=2)); return
    if args.command == 'research' and selected:
        client = sources.Client(ROOT, args.max_cost, model=config['model'], daily=False)
        seeds = federal.read(ROOT / 'config/federal_research_seeds.json', {}).get('subjects', {})
        used_words = Counter()
        for subject in subjects:
            for statement in policy_subjects.load_evidence(ROOT, subject):
                if not official_url(statement['url']):
                    used_words[sources.canonical_url(statement['url'])] += len(statement['text'].split())
        lock = threading.Lock()
        audit_lock = threading.Lock()
        def work(subject):
            pid = subject['id']
            for number in pass_numbers:
                if args.reverify and not (ROOT / 'data/raw/federal_research' / pid / f'pass-{number}.json').exists():
                    continue
                if not args.refresh and not args.reverify and audit['profiles'].get(pid, {}).get('passes', {}).get(str(number), {}).get('status') == 'completed':
                    continue
                try:
                    entry = research_one(ROOT, subject, seeds.get(pid, []), client, config, number, lock, used_words, args.refresh)
                    print(f"{pid} pass {number}: added {len(entry['added_sids'])}, rejected {entry['rejected']}, searches {entry['searches']}", flush=True)
                except Exception as exc:
                    entry = {'status': 'needs_retry', 'date': federal.today(), 'error': type(exc).__name__}
                    print(f'{pid} pass {number}: {type(exc).__name__}: {str(exc)[:180]}', flush=True)
                with audit_lock:
                    record_pass(audit, pid, number, entry)
                    federal.write(audit_path, audit)
                    federal.write(ROOT / 'data/federal_coverage.json', {**coverage(ROOT, subjects, audit), 'methodology': config})
            return pid
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            tasks = {executor.submit(work, s): s for s in selected}
            for future in as_completed(tasks):
                future.result()
    report = coverage(ROOT, subjects, audit)
    federal.write(ROOT / 'data/federal_coverage.json', {**report, 'methodology': config})
    print(json.dumps(report['summary'], indent=2))
    if args.command == 'research' and any(
            audit['profiles'].get(s['id'], {}).get('passes', {}).get(str(n), {}).get('status') != 'completed'
            for s in selected for n in pass_numbers
            if not args.reverify or (ROOT / 'data/raw/federal_research' / s['id'] / f'pass-{n}.json').exists()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
