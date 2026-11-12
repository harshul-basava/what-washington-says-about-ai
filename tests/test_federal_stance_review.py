import json
import unittest

import federal_stance_review as review


class StanceReviewTests(unittest.TestCase):
    def test_prompt_shares_full_source_text_without_losing_per_excerpt_proof(self):
        text='Official A said: AI will benefit our whole economy. '*1000
        contexts={
            's1':{'status':'available','url':'https://example.gov/a','text':text,'verified_author_id':'7'},
            's2':{'status':'available','url':'https://example.gov/a','text':text,'shared_from_sid':'s1'},
            's3':{'status':'available','url':'https://example.gov/b','text':text+'Distinct ending.'},
            's4':{'status':'unavailable','url':'https://example.gov/c','reason':'HTTP 403'}}
        messages=review.review_messages({'id':'test','name':'Official A'},[],contexts,{'prompt':'Prompt','rubric':'Rubric'})
        payload=json.loads(messages[-1]['content'])
        documents=payload['retrieved_source_documents']
        self.assertEqual(len(documents),2)
        self.assertEqual(payload['retrieved_source_context']['s1']['text_ref'],payload['retrieved_source_context']['s2']['text_ref'])
        restored={}
        for sid,row in payload['retrieved_source_context'].items():
            row=dict(row)
            if 'text_ref' in row:row['text']=documents[row.pop('text_ref')]
            restored[sid]=row
        self.assertEqual(restored,contexts)
        self.assertLess(len(messages[-1]['content']),len(json.dumps(contexts))*.75)

    def result(self):
        return {'findings':[{'sid':'s1','label':3,'confidence':4,'reason':'General benefits.',
                             'supporting_quote':'AI will benefit our whole economy.'}],
                'no_stance_sids':['s2'],'context_requests':[], 'confidence':4,
                'reason':'One general stance and one technical statement.',
                'summary_sentences':[{'text':'The subject expects broad benefits from AI.','sids':['s1']}]}

    def test_review_requires_exact_statement_coverage_and_verbatim_support(self):
        ss=[{'sid':'s1','text':'AI will benefit our whole economy.'},{'sid':'s2','text':'An AI chip rule.'}]
        result=review.parse_review(json.dumps(self.result()),ss,{})
        self.assertEqual(result['findings'][0]['label'],3)
        for mutate in [lambda x:x['no_stance_sids'].clear(),
                       lambda x:x['findings'][0].update(supporting_quote='Invented quote'),
                       lambda x:x['findings'][0].update(label=True),
                       lambda x:x['context_requests'].append({'sid':'s1','reason':'Duplicate'})]:
            payload=self.result();mutate(payload)
            with self.assertRaises(ValueError):review.parse_review(json.dumps(payload),ss,{})

    def test_missing_context_cannot_be_silently_treated_as_a_stance(self):
        ss=[{'sid':'s1','text':'It is a Trojan horse.'}]
        payload={'findings':[],'no_stance_sids':[],
                 'context_requests':[{'sid':'s1','reason':'Need to identify the object.'}],
                 'confidence':2,'reason':'Ambiguous excerpt.',
                 'summary_sentences':[{'text':'The excerpt lacks context.','sids':['s1']}]}
        result=review.parse_review(json.dumps(payload),ss,{})
        self.assertEqual(len(result['context_requests']),1)
        self.assertEqual(result['findings'],[])

    def test_context_support_requires_retrieved_text_and_same_speaker_attribution(self):
        ss=[{'sid':'s1','text':'An AI chip rule.'},{'sid':'s2','text':'Another rule.'}]
        context={'s1':{'status':'available','text':'Official A said: AI will benefit our whole economy.'}}
        payload=self.result();payload['findings'][0]['attribution_quote']='Official A said: AI will benefit our whole economy.'
        result=review.parse_review(json.dumps(payload),ss,context)
        self.assertEqual(result['findings'][0]['support_basis'],'context')
        del payload['findings'][0]['attribution_quote']
        with self.assertRaises(ValueError):review.parse_review(json.dumps(payload),ss,context)

    def test_context_failure_identifies_the_statement_and_failed_checks(self):
        ss=[{'sid':'s1','text':'An AI chip rule.'},{'sid':'s2','text':'Another rule.'}]
        payload=self.result()
        with self.assertRaisesRegex(ValueError, r's1: context_available=False, quote_found=False, attribution_found=False'):
            review.parse_review(json.dumps(payload),ss,{})
        context={'s1':{'status':'available','text':'Official A said: AI will benefit our whole economy.'}}
        with self.assertRaisesRegex(ValueError, r's1: context_available=True, quote_found=True, attribution_found=False'):
            review.parse_review(json.dumps(payload),ss,context)

    def test_x_context_checks_original_author_and_post_id(self):
        statement={'post_id':'123','text':'AI helps','attribution':{'user_id':'7'}}
        post={'id':'123','author_id':'7','text':'AI helps people across our economy.'}
        self.assertEqual(review.verified_post_text(statement,post),post['text'])
        with self.assertRaises(ValueError):review.verified_post_text(statement,{**post,'author_id':'8'})
        with self.assertRaises(ValueError):review.verified_post_text(statement,{**post,'id':'999'})
        with self.assertRaises(ValueError):review.verified_post_text(statement,{**post,'text':'Unrelated content'})

    def test_verified_x_author_can_establish_context_attribution(self):
        ss=[{'sid':'s1','text':'An AI chip rule.','source_type':'x','url':'https://x.com/a/status/123',
             'attribution':{'user_id':'7'}},{'sid':'s2','text':'Another rule.'}]
        context={'s1':{'status':'available','url':ss[0]['url'],
            'text':'An AI chip rule. AI will benefit our whole economy.',
            'retrieval':'official_x_api_post_and_author','verified_author_id':'7'}}
        result=review.parse_review(json.dumps(self.result()),ss,context)
        self.assertEqual(result['findings'][0]['support_basis'],'context')
        for field,bad in [('verified_author_id','8'),('url','https://x.com/a/status/999'),
                          ('retrieval','unverified_search_snippet')]:
            changed={'s1':{**context['s1'],field:bad}}
            with self.assertRaises(ValueError):review.parse_review(json.dumps(self.result()),ss,changed)
