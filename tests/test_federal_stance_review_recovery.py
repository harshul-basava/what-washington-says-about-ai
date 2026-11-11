import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx

import federal_stance_review as review


class ContextRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.subject = {'id': 'a', 'name': 'Official A', 'entity_type': 'person', 'roles': []}
        self.statement = {'sid': 's1', 'text': 'An AI chip rule.',
                          'url': 'https://agency.gov/speech', 'source_type': 'official_statement'}
        self.text = 'Official A describes an AI chip rule. An AI chip rule. ' + 'Wider source context. ' * 8
        self.config = {'rubric': 'Original rubric', 'prompt': 'Original prompt'}
        self.cache = self.root / 'data/raw/federal_stance_context/a/s1.json'
        self.meta = {'status': 'available', 'url': self.statement['url'], 'retrieval': 'direct_page',
                     'text_hash': review.a.digest(review.normalize(self.text)),
                     'cache_path': str(self.cache.relative_to(self.root)), 'retrieved_at': 'original-time'}
        contexts = {'s1': {**self.meta, 'text': review.normalize(self.text)}}
        self.entry = {'model': review.MODEL, 'generation_id': 'original-generation',
                      'contexts': {'s1': self.meta}, 'result': self.response(),
                      'evidence_hash': review.a.digest([self.statement]), 'applied_review_id': 'original-review'}
        self.entry['input_hash'] = review.a.digest([
            review.PROMPT_VERSION, review.MODEL, review.a.subject_context(self.subject),
            [self.statement], contexts, self.config['rubric'], self.config['prompt']])
        self.audit = {'target_ids': ['a'], 'profiles': {'a': self.entry}, 'budget_baseline': 0}
        review.a.write(self.root / review.PATH, self.audit)
        self.enterContext(patch.object(review.a, 'inputs', return_value=([self.subject], {'a': [self.statement]})))
        self.enterContext(patch.object(review.a, 'configuration', return_value=self.config))

    def response(self):
        return {'findings': [], 'no_stance_sids': ['s1'], 'context_requests': [],
                'confidence': 4, 'reason': 'The excerpt describes one rule.',
                'summary_sentences': [{'text': 'The official describes an AI rule.', 'sids': ['s1']}]}

    def source_response(self, url, **kwargs):
        if url.endswith('/models'):
            return httpx.Response(200, json={'data': [{'id': review.MODEL}]}, request=httpx.Request('GET', url))
        return httpx.Response(200, text='<p>' + self.text + '</p>', request=httpx.Request('GET', url))

    def test_missing_resolved_web_context_is_restored_without_rebuying_unchanged_review(self):
        with patch('httpx.get', side_effect=self.source_response), patch.object(review, 'Budget', side_effect=AssertionError('Unchanged review must remain cached')):
            saved = review.run(self.root, max_cost=1)
        self.assertEqual(review.a.read(self.cache)['text'], review.normalize(self.text))
        self.assertEqual(saved['profiles']['a'], self.entry)

    def test_parallel_model_reviews_keep_source_recovery_at_four_workers(self):
        with patch('httpx.get', side_effect=self.source_response), \
             patch.object(review, 'Budget', side_effect=AssertionError('Unchanged review must remain cached')), \
             patch.object(review, 'fetch_contexts', wraps=review.fetch_contexts) as fetch:
            saved = review.run(self.root, max_cost=1, workers=20)
        self.assertEqual(fetch.call_args.kwargs['workers'], 4)
        self.assertEqual(saved['profiles']['a'], self.entry)

    def test_changed_recovered_text_requires_a_new_review_and_keeps_prior_provenance(self):
        self.text += ' Additional source text changed after the original review.'
        prompts = []

        class Budget:
            def __init__(self, *args, wait_for_capacity=False):
                pass

            def call(inner, model, messages, *args, **kwargs):
                prompts.append(json.loads(messages[1]['content']))
                return {'id': 'new-generation', 'choices': [{'message': {'content': json.dumps(self.response())}}]}

        with patch('httpx.get', side_effect=self.source_response), patch.object(review, 'Budget', Budget), patch('llm.spent', return_value=0):
            saved = review.run(self.root, max_cost=1)
        entry = saved['profiles']['a']
        self.assertEqual(prompts[0]['retrieved_source_context']['s1']['text'], review.normalize(self.text))
        self.assertNotEqual(entry['input_hash'], self.entry['input_hash'])
        self.assertEqual(entry['previous_reviews'], [self.entry])
        self.assertNotIn('applied_review_id', entry)
        with self.assertRaises(ValueError):
            review.load_contexts(self.root, self.entry['contexts'])

    def test_same_page_context_is_saved_for_each_matching_excerpt_and_reused(self):
        second = {**self.statement, 'sid': 's2', 'text': 'AI will benefit'}
        self.text += ' Official A said: AI will benefit our whole economy.'
        self.meta['text_hash'] = review.a.digest(review.normalize(self.text))
        self.entry['error'] = 'An earlier context review needs retry'
        review.a.write(self.cache, {'status': 'available', 'url': self.statement['url'], 'text': review.normalize(self.text)})
        review.a.write(self.root / review.PATH, self.audit)
        result = self.response()
        result['findings'] = [{'sid': 's2', 'label': 3, 'confidence': 4, 'reason': 'General benefits.',
                              'supporting_quote': 'AI will benefit our whole economy.',
                              'attribution_quote': 'Official A said: AI will benefit our whole economy.'}]
        class Budget:
            def __init__(self, *args, **kwargs): pass
            def call(inner, *args, **kwargs):
                return {'id': 'shared-generation', 'choices': [{'message': {'content': json.dumps(result)}}]}
        with patch.object(review.a, 'inputs', return_value=([self.subject], {'a': [self.statement, second]})), \
             patch('httpx.get', side_effect=self.source_response), patch.object(review, 'Budget', Budget), \
             patch('llm.spent', return_value=0):
            saved = review.run(self.root, max_cost=1)
            entry = saved['profiles']['a']
            self.assertNotIn('error', entry)
            self.assertEqual(entry['contexts']['s2'], {**self.meta, 'shared_from_sid': 's1'})
            self.assertEqual(entry['result']['findings'][0]['support_basis'], 'context')
            with patch.object(review, 'Budget', side_effect=AssertionError('Shared context must remain cached')):
                self.assertEqual(review.run(self.root, max_cost=1)['profiles']['a'], entry)

    def test_context_sharing_requires_same_url_exact_excerpts_and_verified_cache(self):
        review.a.write(self.cache, {'status': 'available', 'url': self.statement['url'], 'text': review.normalize(self.text)})
        metadata = {'s1': self.meta}
        for second in (
            {**self.statement, 'sid': 's2', 'url': 'https://other.gov/speech'},
            {**self.statement, 'sid': 's2', 'text': 'Words absent from the source'},
            {**self.statement, 'sid': 's2', 'source_type': 'x'},
        ):
            with self.subTest(second=second):
                shared = review.share_source_contexts(self.root, [self.statement, second], metadata)
                self.assertNotIn('s2', shared)
        second = {**self.statement, 'sid': 's2'}
        shared = review.share_source_contexts(self.root, [{**self.statement, 'source_type': 'x'}, second], metadata)
        self.assertNotIn('s2', shared)
        unavailable = {**metadata, 's2': {'status': 'unavailable', 'reason': 'Keep this explicit source gap'}}
        self.assertEqual(review.share_source_contexts(self.root, [self.statement, second], unavailable), unavailable)
        review.a.write(self.cache, {'status': 'available', 'url': 'https://other.gov/speech', 'text': review.normalize(self.text)})
        self.assertNotIn('s2', review.share_source_contexts(self.root, [self.statement, second], metadata))
        review.a.write(self.cache, {'status': 'available', 'url': self.statement['url'], 'text': 'Changed cache'})
        with self.assertRaises(ValueError):
            review.share_source_contexts(self.root, [self.statement, {**self.statement, 'sid': 's2'}], metadata)

    def test_existing_changed_cache_is_retrieved_again_before_review(self):
        review.a.write(self.cache, {'status': 'available', 'url': self.statement['url'], 'text': 'Changed cache content'})
        with patch('httpx.get', side_effect=self.source_response), patch.object(review, 'Budget', side_effect=AssertionError('Original source restores the cached review')):
            saved = review.run(self.root, max_cost=1)
        self.assertEqual(saved['profiles']['a'], self.entry)
        self.assertEqual(review.a.read(self.cache)['text'], review.normalize(self.text))

    def test_recovery_keeps_unavailable_context_explicit(self):
        def unavailable(url, **kwargs):
            if url.endswith('/models'):
                raise AssertionError('Test recovery without inference')
            return httpx.Response(403, request=httpx.Request('GET', url))

        with patch('httpx.get', side_effect=unavailable):
            recovered = review.recover_contexts(self.root, self.audit, {'a': [self.statement]}, {'a'}, 1)
        self.assertEqual(recovered['a']['s1']['status'], 'unavailable')
        self.assertEqual(review.a.read(self.root / review.PATH)['profiles']['a'], self.entry)
        with self.assertRaises(ValueError):
            review.load_contexts(self.root, self.entry['contexts'])

    def test_resolved_x_recovery_rechecks_the_official_post_author(self):
        self.statement.update(source_type='x', url='https://x.com/a/status/123', post_id='123', attribution={'user_id': '7'})
        self.meta.update(url=self.statement['url'], retrieval='official_x_api_post_and_author', verified_author_id='7')
        review.a.write(self.root / review.PATH, self.audit)
        ledger = self.root / 'ledger.jsonl'
        ledger.write_text('')

        class XClient:
            spent = 0

            def __init__(self, *args, **kwargs):
                pass

            def request(inner, *args):
                return {'data': {'id': '123', 'author_id': '8', 'text': self.text}}

        with patch('scripts.federal_x_api.Client', XClient), patch('llm.LEDGER', ledger), patch('httpx.get', side_effect=AssertionError('X recovery uses the official transport')):
            recovered = review.recover_contexts(self.root, self.audit, {'a': [self.statement]}, {'a'}, 1)
        self.assertEqual(recovered['a']['s1']['status'], 'unavailable')
        self.assertNotIn('verified_author_id', recovered['a']['s1'])

    def test_resolved_x_recovery_retains_verified_author_and_text(self):
        self.statement.update(source_type='x', url='https://x.com/a/status/123', post_id='123', attribution={'user_id': '7'})
        self.meta.update(url=self.statement['url'], retrieval='official_x_api_post_and_author', verified_author_id='7')
        review.a.write(self.root / review.PATH, self.audit)
        ledger = self.root / 'ledger.jsonl'
        ledger.write_text('')

        class XClient:
            spent = 0

            def __init__(self, *args, **kwargs):
                pass

            def request(inner, *args):
                return {'data': {'id': '123', 'author_id': '7', 'text': self.text}}

        with patch('scripts.federal_x_api.Client', XClient), patch('llm.LEDGER', ledger), patch('httpx.get', side_effect=AssertionError('X recovery uses the official transport')):
            recovered = review.recover_contexts(self.root, self.audit, {'a': [self.statement]}, {'a'}, 1)
        contexts = review.load_contexts(self.root, recovered['a'])
        self.assertEqual(contexts['s1']['verified_author_id'], '7')
        self.assertEqual(contexts['s1']['text'], review.normalize(self.text))
        self.assertEqual(recovered['a']['s1'], self.meta)

    def test_unapplied_changed_context_cannot_reuse_a_saved_review(self):
        self.text += ' Changed source content.'
        with patch('httpx.get', side_effect=self.source_response):
            review.recover_contexts(self.root, self.audit, {'a': [self.statement]}, {'a'}, 1)
        with self.assertRaisesRegex(ValueError, 'Context cache changed'):
            review.apply(self.root)
        self.assertEqual(review.a.read(self.root / review.PATH)['profiles']['a'], self.entry)

    def test_original_outstanding_context_request_flow_remains_available(self):
        audit = {'target_ids': ['a'], 'profiles': {'a': {'result': {'context_requests': [{'sid': 's1'}]}}}}
        review.a.write(self.root / review.PATH, audit)
        with patch('httpx.get', side_effect=self.source_response):
            review.fetch_contexts(self.root, workers=1)
        index = review.a.read(self.root / 'data/raw/federal_stance_context/index.json')
        self.assertEqual(index['a']['s1']['status'], 'available')
        self.assertEqual(review.load_contexts(self.root, index['a'])['s1']['text'], review.normalize(self.text))


if __name__ == '__main__':
    unittest.main()
