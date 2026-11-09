import unittest


class StanceSearchTests(unittest.TestCase):
    def test_account_queries_preserve_ownership_dates_and_unmapped_profiles_only_get_leads(self):
        import federal_stance_search as s
        subjects={'a':{'id':'a','name':'Official A'},'b':{'id':'b','name':'Official B'}}
        accounts=[{'id':'a_office','subject_id':'a','handle':'OfficialA','valid_from':'2025-02-01','valid_until':'2026-01-01'}]
        jobs=s.search_jobs(subjects,accounts,'2026-11-09')
        authored=[j for j in jobs if j['kind']=='account']
        self.assertEqual(len(authored),2)
        self.assertTrue(all(j['start']=='2025-02-01' and j['end']=='2026-01-01' for j in authored))
        self.assertTrue(all(j['query'].startswith('from:OfficialA ') for j in authored))
        leads=[j for j in jobs if j['kind']=='mention']
        self.assertEqual([j['subject_id'] for j in leads],['b'])
        self.assertNotIn('from:',leads[0]['query'])

    def test_search_job_keys_change_with_query_or_interval(self):
        import federal_stance_search as s
        subjects={'a':{'id':'a','name':'Official A'}}
        before=s.search_jobs(subjects,[],'2026-11-09')[0]
        after=s.search_jobs(subjects,[],'2026-11-10')[0]
        self.assertNotEqual(before['id'],after['id'])

    def test_source_reviews_require_exact_url_coverage_and_verbatim_support(self):
        import federal_stance_search as s
        pages=[{'url':'https://example.gov/speech','text':'Official A says AI can benefit our whole society.'}]
        rows={'pages':[{'url':pages[0]['url'],'reason':'A broad stance.', 'statements':[{
            'quote':'AI can benefit our whole society.','attribution_quote':pages[0]['text'],
            'ai_overall':3,'confidence':4,'reason':'Broad benefit.'}]}]}
        self.assertEqual(len(s.validate_source_review(rows,pages)),1)
        rows['pages'][0]['statements'][0]['quote']='Invented words'
        with self.assertRaises(ValueError):s.validate_source_review(rows,pages)
        with self.assertRaises(ValueError):s.validate_source_review({'pages':[]},pages)

