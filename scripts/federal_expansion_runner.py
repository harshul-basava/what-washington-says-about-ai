"""Run one authorized federal expansion cohort with one shared model allowance."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
STAGES = ('research', 'seeds', 'analysis', 'policies', 'astra')


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else ({} if default is None else default)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def select_ids(manifest, cohort, eligible):
    if cohort == 'existing_refresh':
        added = {pid for c in manifest['cohorts'] if c['id'].startswith('expansion_') for pid in c['subject_ids']}
        return sorted(set(eligible) - added)
    matches = [c for c in manifest['cohorts'] if c['id'] == cohort and c['id'].startswith('expansion_')]
    if len(matches) != 1:
        raise ValueError('Unknown expansion cohort')
    ids = matches[0]['subject_ids']
    if not ids or len(ids) != len(set(ids)) or not set(ids) <= set(eligible):
        raise ValueError('Cohort has duplicate, missing, or excluded profiles')
    return ids


def remaining_allowance(limit, baseline, spent):
    if not all(math.isfinite(v) for v in (limit, baseline, spent)) or spent < baseline - 1e-8:
        raise ValueError('Invalid or regressed model ledger')
    return max(0, limit - (spent - baseline))


def restore_seed_checkpoints(root, ids):
    saved = read(root / 'data/federal_seed_research.json').get('profiles', {})
    for pid in ids:
        path = root / f'data/raw/federal_research/{pid}/seeds.json'
        if not path.exists() and pid in saved:
            checkpoint = {k: saved[pid][k] for k in ('sources', 'added_sids')}
            for row in checkpoint['sources'].values():
                if row.get('status') != 'completed':
                    row['next_chunk'] = 0
            write(path, checkpoint)


def merge_contexts(root, audit):
    index = read(root / 'data/raw/federal_stance_context/index.json')
    for pid in audit['target_ids']:
        if pid in audit['profiles']:
            audit['profiles'][pid].setdefault('contexts', {}).update(index.get(pid, {}))


def web_pending(root, ids):
    profiles = read(root / 'data/federal_research.json').get('profiles', {})
    return {pid: [n for n in range(1, 9) if profiles.get(pid, {}).get('passes', {}).get(str(n), {}).get('status') != 'completed']
            for pid in ids if any(profiles.get(pid, {}).get('passes', {}).get(str(n), {}).get('status') != 'completed' for n in range(1, 9))}


def seed_gaps(root, ids, run_token=None):
    profiles = read(root / 'data/federal_seed_research.json').get('profiles', {})
    missing = [{'id': pid, 'error': 'missing_checkpoint', 'stage': 'setup'}
               for pid in ids if pid not in profiles or 'sources' not in profiles[pid]]
    missing.extend({'id': pid, 'error': 'missing_current_checkpoint', 'stage': 'setup'}
                   for pid in ids if pid in profiles and run_token is not None and profiles[pid].get('run_token') != run_token)
    return missing + [{'id': pid, 'url': url, 'error': row.get('error', 'incomplete'),
                      'stage': row.get('error_stage', 'unknown')}
            for pid in ids for url, row in profiles.get(pid, {}).get('sources', {}).items()
            if row.get('status') != 'completed']


def command(root, script, *args, capture=False):
    result = subprocess.run([sys.executable, str(root / script), *map(str, args)], cwd=root,
                            text=True, capture_output=capture)
    if capture:
        if result.returncode:
            raise RuntimeError('Read-only prerequisite failed: ' + script)
        return json.loads(result.stdout)
    return result.returncode


def review_cohort(root, cohort, ids, allowance, workers, refresh_ids):
    import federal_analysis as analysis
    import federal_stance_review as review
    import llm
    subjects, evidence = analysis.inputs(root)
    byid = {s['id']: s for s in subjects}
    path = root / f'data/federal_roster_expansion_review_{cohort}.json'
    audit = read(path)
    target_ids = [pid for pid in ids if evidence[pid] and
                  (cohort != 'existing_refresh' or pid in refresh_ids)]
    # A retry retains the original review targets, even after labels become complete.
    target_ids = list(dict.fromkeys(audit.get('target_ids', []) + target_ids))
    if not set(target_ids) <= set(ids):
        raise ValueError('Saved review targets left the selected current cohort')
    if not target_ids:
        return {'status': 'complete', 'reviewed_profiles': 0}
    index = analysis.build(root)
    scores = {m['id']: m['scores'] for m in index['members']}
    if not audit:
        audit = {'version': 1, 'prompt_version': review.PROMPT_VERSION, 'model': review.MODEL,
                 'dimension': 'ai_overall', 'created_at': datetime.now(timezone.utc).isoformat(),
                 'budget_baseline': llm.spent('openrouter'), 'source_revision': index['revision'],
                 'target_ids': [], 'original_scores': {}, 'profiles': {},
                 'change_cause': 'Astra review after federal roster expansion research'}
    audit['target_ids'] = target_ids
    for pid in target_ids:
        audit['original_scores'].setdefault(pid, scores[pid])
    write(path, audit)
    review.PATH = str(path.relative_to(root))
    for _ in range(3):
        remaining = allowance()
        if remaining <= 0:
            return {'status': 'pending', 'reason': 'model_allowance_exhausted'}
        # The review API measures its allowance from the saved audit baseline.
        review.run(root, llm.spent('openrouter') - audit['budget_baseline'] + remaining,
                   workers=workers, ids=target_ids)
        audit = read(path)
        if any(not audit['profiles'].get(pid, {}).get('result') or audit['profiles'][pid].get('error') for pid in target_ids):
            return {'status': 'pending', 'reason': 'review_response_incomplete'}
        requests = [(pid, row) for pid in target_ids for row in audit['profiles'][pid]['result']['context_requests']]
        if not requests:
            result = review.apply(root)
            analysis.build(root, record=True)
            return {'status': 'complete', **result}
        review.fetch_contexts(root, workers=min(workers, 4))
        if any(next(s for s in evidence[pid] if s['sid'] == row['sid']).get('source_type') == 'x' for pid, row in requests):
            review.fetch_x_context(root)
            review.fetch_contexts(root, workers=min(workers, 4))
        merge_contexts(root, audit)
        write(path, audit)
    return {'status': 'pending', 'reason': 'source_context_still_requested'}


def run(root, cohort, ids, stages, max_cost, workers):
    import federal_analysis as analysis
    import llm
    root = Path(root)
    credit = command(root, 'scripts/openrouter_credit_check.py', '--required-credit=0', capture=True)
    lifetime = [b for b in credit.get('guardrail_budgets', []) if b['scope'] == 'workspace' and b['reset_interval'] is None]
    if len(lifetime) != 1 or lifetime[0]['limit_usd'] != 350 or credit['spendable_usd'] <= 0:
        raise ValueError('The authorized workspace allowance is not available')
    limit = min(max_cost, credit['spendable_usd'])
    baseline = llm.spent('openrouter')
    allowance = lambda: remaining_allowance(limit, baseline, llm.spent('openrouter'))
    status_path = root / 'data/federal_backfill_status.json'
    saved = read(status_path, {'version': 1, 'cohorts': {}})
    previous = saved['cohorts'].get(cohort, {})
    attempt = {'started_at': datetime.now(timezone.utc).isoformat(), 'subject_ids': ids,
               'requested_stages': stages, 'model_allowance_usd': limit, 'model_baseline': baseline,
               'stages': {}, 'status': 'in_progress'}
    saved['cohorts'][cohort] = {**attempt, 'previous_attempts': previous.get('previous_attempts', []) + ([{k: v for k, v in previous.items() if k != 'previous_attempts'}] if previous else [])}
    attempt = saved['cohorts'][cohort]
    def checkpoint():
        attempt['model_cost_usd'] = round(llm.spent('openrouter') - baseline, 6)
        attempt['updated_at'] = datetime.now(timezone.utc).isoformat()
        write(status_path, saved)
    checkpoint()
    subjects, evidence = analysis.inputs(root)
    config = analysis.configuration(root)
    labels, _ = analysis.state(root)
    manifest = read(root / 'data/federal_roster_expansion.json')
    refresh_ids = set(previous.get('refresh_review_ids', [])) | set(manifest.get('role_context_refresh_ids', []))
    for subject in subjects:
        pid = subject['id']
        if pid in ids and subject['entity_type'] == 'person' and any(
                analysis.resolve_labels(analysis.valid_entry(labels, subject, [s], 'labels', config), config['settings'])['status'] != 'complete'
                for s in evidence[pid]):
            refresh_ids.add(pid)
    attempt['refresh_review_ids'] = sorted(refresh_ids.intersection(ids))
    try:
        for stage in stages:
            if allowance() <= 0:
                attempt['status'] = 'pending_budget'; break
            if stage in ('research', 'seeds') and cohort == 'existing_refresh':
                attempt['stages'][stage] = {'status': 'not_requested_for_retained_profiles'}; checkpoint(); continue
            if stage == 'research':
                code = command(root, 'scripts/federal_research.py', 'research', '--ids', ','.join(ids), '--rounds', 8,
                               '--workers', workers, '--max-cost', allowance())
                pending = web_pending(root, ids)
                attempt['stages'][stage] = {'status': 'complete' if not pending else 'pending', 'pending_passes': pending, 'exit_code': code}
                if pending:
                    attempt['status'] = 'research_pending'; checkpoint(); break
            elif stage == 'seeds':
                restore_seed_checkpoints(root, ids)
                run_token = uuid.uuid4().hex
                code = command(root, 'scripts/federal_research.py', 'seeds', '--ids', ','.join(ids),
                               '--workers', workers, '--max-cost', allowance(), '--run-token', run_token)
                reverify_code = command(root, 'scripts/federal_reverify_cache.py', '--ids', ','.join(ids))
                gaps = seed_gaps(root, ids, run_token)
                attempt['stages'][stage] = {'status': 'complete_with_source_gaps' if gaps else 'complete',
                                           'source_gaps': gaps, 'exit_code': code, 'cache_reverification_exit_code': reverify_code}
                if reverify_code or any(g['stage'] != 'source_fetch' or g['error'] in ('BudgetExceeded', 'OpenRouterRequestError') for g in gaps):
                    attempt['stages'][stage]['status'] = 'pending'; attempt['status'] = 'seed_models_pending'; checkpoint(); break
            elif stage == 'analysis':
                code = command(root, 'scripts/federal_analysis.py', 'label', '--ids', ','.join(ids),
                               '--workers', workers, '--max-cost', allowance())
                report = analysis.plan(root, set(ids))
                attempt['stages'][stage] = {'status': 'complete' if report['status'] == 'ok' else 'pending', 'coverage': report, 'exit_code': code}
                if report['status'] != 'ok':
                    attempt['status'] = 'analysis_pending'; checkpoint(); break
            elif stage == 'policies':
                code = command(root, 'scripts/phase3_policies.py', 'label', '--scope', 'executive', '--ids', ','.join(ids),
                               '--workers', min(workers, 4), '--max-cost', allowance())
                report = command(root, 'scripts/phase3_policies.py', 'plan', '--scope', 'executive', '--ids', ','.join(ids), capture=True)
                attempt['stages'][stage] = {'status': 'complete' if report['uncached_requests'] == 0 else 'pending', 'pending_requests': report['uncached_requests'], 'exit_code': code}
                if report['uncached_requests']:
                    attempt['status'] = 'policy_models_pending'; checkpoint(); break
            else:
                if analysis.plan(root, set(ids))['status'] != 'ok':
                    attempt['status'] = 'analysis_required_before_astra'; checkpoint(); break
                result = review_cohort(root, cohort, ids, allowance, workers, refresh_ids)
                attempt['stages'][stage] = result
                if result['status'] != 'complete':
                    attempt['status'] = 'astra_pending'; checkpoint(); break
            checkpoint()
        else:
            attempt['status'] = 'requested_stages_complete'
    except Exception as exc:
        attempt.update(status='incomplete', error=type(exc).__name__)
        raise
    finally:
        checkpoint()
    # Manifest stages describe actual outputs, not merely a successful command exit.
    manifest = read(root / 'data/federal_roster_expansion.json')
    seed_profiles = read(root / 'data/federal_seed_research.json').get('profiles', {})
    audit = read(root / f'data/federal_roster_expansion_review_{cohort}.json')
    for pid in ids:
        if pid not in manifest['profiles']:
            continue
        row = manifest['profiles'][pid]
        pending = web_pending(root, [pid])
        row.update(web='complete_eight_passes' if not pending else 'pending',
                   web_passes_completed=8 - len(pending.get(pid, [])),
                   source_pages_pending=seed_profiles.get(pid, {}).get('sources_pending', 0))
        row['analysis'] = 'complete' if analysis.plan(root, {pid})['status'] == 'ok' else 'pending'
        ss = read(root / f'evidence/{pid}.json').get('statements', [])
        row['n_statements'] = len(ss)
        if not ss:
            row['astra'] = 'no_evidence_to_review'
        elif cohort != 'existing_refresh' or pid in refresh_ids:
            reviewed = audit.get('profiles', {}).get(pid, {})
            row['astra'] = 'complete' if (
                attempt['stages'].get('astra', {}).get('status') == 'complete'
                and reviewed.get('applied_review_id')
                and reviewed.get('evidence_hash') == analysis.digest(ss)) else 'pending'
    for entry in manifest['cohorts']:
        if entry['id'] == cohort:
            entry['last_backfill_status'] = attempt['status']
            entry['status'] = 'complete_with_source_gaps' if attempt['status'] == 'requested_stages_complete' and set(stages) == set(STAGES) and seed_gaps(root, ids) else (
                'complete' if attempt['status'] == 'requested_stages_complete' and set(stages) == set(STAGES) else 'in_progress')
    manifest['funding_status'].update(state='authorized_workspace_cap_confirmed', current_workspace_lifetime_cap_usd=350,
                                      note='Original repository credit check confirmed the approved $350 workspace cap. Research runs share existing provider and repository limits; each batch records its own remaining stages.')
    write(root / 'data/federal_roster_expansion.json', manifest)
    return attempt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('plan', 'run'))
    parser.add_argument('--cohort', required=True)
    parser.add_argument('--max-cost', type=float, default=25)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--stages', default=','.join(STAGES))
    args = parser.parse_args()
    if not math.isfinite(args.max_cost) or not 0 < args.max_cost <= 25 or not 1 <= args.workers <= 20:
        parser.error('Use max-cost greater than zero and at most 25; workers must be 1–20')
    requested = args.stages.split(',')
    if not requested or len(requested) != len(set(requested)) or not set(requested) <= set(STAGES):
        parser.error('Invalid or duplicate stages')
    stages = [s for s in STAGES if s in requested]
    import policy_subjects
    eligible = {s['id'] for s in policy_subjects.load_subjects(ROOT) if s['branch'] == 'executive'}
    ids = select_ids(read(ROOT / 'data/federal_roster_expansion.json'), args.cohort, eligible)
    if args.command == 'plan':
        result = {'cohort': args.cohort, 'subject_ids': ids, 'count': len(ids), 'stages': stages,
                  'pending_web_passes': {} if args.cohort == 'existing_refresh' else web_pending(ROOT, ids),
                  'max_model_cost_usd': args.max_cost, 'workers': args.workers, 'paid_calls': 0}
    else:
        result = run(ROOT, args.cohort, ids, stages, args.max_cost, args.workers)
    print(json.dumps(result, indent=2), flush=True)
    return 0 if args.command == 'plan' or result['status'] == 'requested_stages_complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
