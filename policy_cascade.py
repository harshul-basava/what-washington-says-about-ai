"""Confidence-based policy assessment, with independent escalation and per-pair caches."""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import policy_judgments as p

ROLES = ('deepseek', 'astra')
STAGE_PROMPTS = {
    'deepseek': 'Assess each supplied statement independently using the policy rubric and confidence instructions.',
    'astra': 'Independently assess each supplied statement using the policy rubric and confidence instructions. You receive no other model answer. Return your own evidence-based classification.'}


def load_strategy(root):
    path = Path(root) / 'config/policy_judging.json'
    if not path.exists():
        return None
    config = p.read_json(path)
    threshold = config.get('threshold')
    if (config.get('kind') != 'confidence_cascade' or config.get('version') != 1 or
            type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0 < threshold <= 1):
        raise ValueError('Invalid policy strategy or threshold; use a number above 0 and at most 1')
    for key in ('primary_model', 'reviewer_model'):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError('Both policy model IDs are required')
    return config


def models(strategy):
    return {'deepseek': strategy['primary_model'], 'astra': strategy['reviewer_model']}


def messages(items, registry, rubric, confidence_prompt, role):
    return p.messages(items, registry, rubric + '\n\n' + confidence_prompt + '\n\n' + STAGE_PROMPTS[role])


def validate_response(text, items, registry):
    labels = p.validate_response(text, items, registry)
    for targets in labels.values():
        for value in targets.values():
            confidence = value.get('confidence')
            reason = value.get('confidence_reason')
            if type(confidence) not in (int, float) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
                raise ValueError('Every judgment requires numeric confidence between 0 and 1')
            if not isinstance(reason, str) or not reason.strip() or len(reason) > 1500:
                raise ValueError('Every judgment requires a short confidence reason')
    return labels


def input_hash(item, target, role, registry, rubric, confidence_prompt, strategy):
    return p.fingerprint([{**item, 'targets': [target]}], registry,
                         rubric + '\n\n' + confidence_prompt + '\n\n' + STAGE_PROMPTS[role], models(strategy)[role])


def valid_result(item, target, role, saved, registry, rubric, confidence_prompt, strategy):
    result = saved.get('results', {}).get(item['key'], {}).get(target, {}).get(role, {})
    expected_hash = input_hash(item, target, role, registry, rubric, confidence_prompt, strategy)
    if result.get('input_hash') != expected_hash or result.get('model') != models(strategy)[role]:
        return None
    try:
        checked = validate_response(json.dumps({'judgments': [{'key': item['key'], 'targets': {target: result['label']}}]}),
                                    [{**item, 'targets': [target]}], registry)
    except (ValueError, KeyError, TypeError):
        return None
    return checked[item['key']][target] | {k: result[k] for k in ('model', 'judged_at', 'generation_id') if k in result}


def save_result(saved, item, target, role, value, registry, rubric, confidence_prompt, strategy, generation_id):
    entry = {'model': models(strategy)[role],
             'input_hash': input_hash(item, target, role, registry, rubric, confidence_prompt, strategy),
             'judged_at': datetime.now(timezone.utc).isoformat(), 'generation_id': generation_id, 'label': value}
    saved.setdefault('results', {}).setdefault(item['key'], {}).setdefault(target, {})[role] = entry


def jobs(items, saved, registry, rubric, confidence_prompt, strategy, role, batch_size):
    missing = []
    for item in items:
        targets = []
        for target in item['targets']:
            primary = valid_result(item, target, 'deepseek', saved, registry, rubric, confidence_prompt, strategy)
            if role == 'deepseek':
                needed = primary is None
            else:
                needed = bool(primary and primary['confidence'] < strategy['threshold'] and
                              valid_result(item, target, role, saved, registry, rubric, confidence_prompt, strategy) is None)
            if needed:
                targets.append(target)
        if targets:
            missing.append({**item, 'targets': targets})
    return [(role, missing[start:start + batch_size]) for start in range(0, len(missing), batch_size)]


def resolve(item, target, saved, registry, rubric, confidence_prompt, strategy):
    primary = valid_result(item, target, 'deepseek', saved, registry, rubric, confidence_prompt, strategy)
    record = {'strategy': 'confidence_cascade', 'stance': 'pending', 'judges': {}, 'confidence': None,
              'final_judge': None, 'facets_final': [], 'facet_disagreement': False, 'model_disagreement': False,
              'review_required': False, 'review_status': 'awaiting_deepseek', 'review_reason': 'Awaiting the first assessment.'}
    if not primary:
        return record
    record['judges']['deepseek'] = primary
    reviewer = valid_result(item, target, 'astra', saved, registry, rubric, confidence_prompt, strategy)
    if reviewer:
        record['judges']['astra'] = reviewer
        record['model_disagreement'] = primary['stance'] != reviewer['stance']
        record['facet_disagreement'] = set(primary['facets']) != set(reviewer['facets'])
    final, role = primary, 'deepseek'
    record.update(review_status='primary_accepted', review_reason='DeepSeek confidence meets the threshold.')
    if primary['confidence'] < strategy['threshold']:
        record.update(review_status='awaiting_astra', review_reason=f"DeepSeek confidence {primary['confidence']} is below {strategy['threshold']}.")
        if not reviewer:
            return record
        if reviewer['confidence'] < strategy['threshold']:
            record.update(stance='review_required', review_required=True, review_status='human_review_required',
                          confidence=reviewer['confidence'], review_reason=record['review_reason'] + ' Astra also reports confidence below the threshold; human review is required.')
            return record
        final, role = reviewer, 'astra'
        record['review_status'] = 'astra_reviewed'
    if role == 'deepseek' and reviewer:
        record['review_reason'] += ' A previous Astra assessment remains visible; the current threshold accepts DeepSeek.'
    record.update(stance=final['stance'], final_judge=role, confidence=final['confidence'], facets_final=final['facets'])
    return record
