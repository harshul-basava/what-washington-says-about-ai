import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import federal_archives as archive

class ArchiveTests(unittest.TestCase):
    def test_archive_links_require_official_allowlist_and_document_pattern(self):
        html='<a href="/newsevents/speech/barr20260714a.htm#top">AI</a><a href="https://evil.test/barr20260714a.htm">AI</a><a href="/about.htm">About</a>'
        source={'url':'https://www.federalreserve.gov/newsevents/speech/2026-speeches.htm','domains':['federalreserve.gov'],'pattern':r'/newsevents/(speech|testimony)/[a-z]+[0-9]{8}[a-z]\.htm$'}
        self.assertEqual(archive.archive_links(html,source),[{'url':'https://www.federalreserve.gov/newsevents/speech/barr20260714a.htm','title':'AI'}])

    def test_signature_tracks_source_prompt_and_role_changes(self):
        subject={'id':'p','name':'Alice Example','roles':[]}
        first=archive.extraction_signature('text',[subject])
        self.assertNotEqual(first,archive.extraction_signature('changed',[subject]))
        self.assertNotEqual(first,archive.extraction_signature('text',[{**subject,'name':'Other'}]))
        with patch.object(archive.sources,'EXTRACTION_PROMPT','changed'):self.assertNotEqual(first,archive.extraction_signature('text',[subject]))

    def test_negative_result_is_cached_and_no_ai_chunk_needs_no_model(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);page={'url':'https://example.gov/speech','text':'Alice Example says artificial intelligence will improve science.','verified_via':'exact_normalized_page_text'}
            subject={'id':'p','name':'Alice Example','aliases':[],'entity_type':'person','roles':[]}
            calls=[]
            class Client:
                def extract(self,*args,**kw):calls.append(1);return []
            state={};first=archive.process_document(root,page,[subject],state,Client(),max_chunks=10)
            second=archive.process_document(root,page,[subject],state,Client(),max_chunks=10)
            self.assertEqual(len(calls),1);self.assertEqual(first['status'],'complete');self.assertEqual(second['model_requests'],0)
            page={**page,'text':'Alice Example discusses the weather.'}
            archive.process_document(root,page,[subject],{},Client(),max_chunks=10)
            self.assertEqual(len(calls),1)

    def test_rejected_rows_are_cached_but_not_reported_complete(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]
            class Client:
                def extract(self,*args,**kw):calls.append(1);return [{'subject_id':'p','quote':'invented'}]
            page={'url':'https://example.gov/speech','text':'Alice Example discusses artificial intelligence in a lengthy speech.','verified_via':'exact_normalized_page_text'}
            subject={'id':'p','name':'Alice Example','aliases':[],'entity_type':'person','roles':[]}
            state={}
            for _ in range(2):
                result=archive.process_document(Path(d),page,[subject],state,Client(),max_chunks=10)
                self.assertEqual(result['status'],'needs_review');self.assertEqual(result['rejected'],1)
            self.assertEqual(len(calls),1)

    def test_remaining_allowance_never_resets_or_accepts_regressed_ledger(self):
        self.assertEqual(archive.remaining(100,10,104),6)
        self.assertEqual(archive.remaining(100,10,111),0)
        with self.assertRaises(ValueError):archive.remaining(100,10,99)

    def test_partial_document_resumes_without_repeating_completed_chunk(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]
            class Client:
                def extract(self,*args,**kw):calls.append(1);return []
            page={'url':'https://example.gov/speech','text':('Alice Example artificial intelligence. '*800),'verified_via':'exact_normalized_page_text'}
            subject={'id':'p','name':'Alice Example','aliases':[],'entity_type':'person','roles':[]}
            state={}
            self.assertEqual(archive.process_document(Path(d),page,[subject],state,Client(),max_chunks=1)['status'],'pending')
            self.assertEqual(archive.process_document(Path(d),page,[subject],state,Client(),max_chunks=1)['status'],'complete')
            self.assertEqual(len(calls),2)

    def test_source_url_changes_invalidate_extraction(self):
        self.assertNotEqual(archive.extraction_signature('same',[],'https://a.gov/a'),archive.extraction_signature('same',[],'https://a.gov/b'))
        self.assertNotEqual(archive.extraction_signature('same',[],structured_author=None),archive.extraction_signature('same',[],structured_author={'header':'new author'}))

    def test_unmapped_hearing_speaker_is_rejected_even_when_name_is_near_quote(self):
        with tempfile.TemporaryDirectory() as d:
            quote='Alice Example said artificial intelligence will improve public services across the country.'
            class Client:
                def extract(self,*args,**kw):return [{'subject_id':'p','quote':quote,'attribution_quote':quote,'kind':'personal','date':None,'date_quote':None}]
            subject={'id':'p','name':'Alice Example','aliases':[],'entity_type':'person','organization_id':'test','roles':[]}
            page={'url':'https://www.govinfo.gov/content/pkg/CHRG-1/html/CHRG-1.htm','text':quote,'verified_via':'exact_normalized_page_text'}
            result=archive.process_document(Path(d),page,[subject],{},Client())
            self.assertEqual(result['status'],'needs_review');self.assertEqual(result['added'],{})

    def test_exact_verified_excerpt_is_added_once_and_partial_overlap_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'evidence').mkdir();(root/'evidence/p.json').write_text(json.dumps({'id':'p','statements':[]}))
            quote='Alice Example said artificial intelligence will improve public services across the country.'
            class Client:
                def extract(self,*args,**kw):return [{'subject_id':'p','quote':quote,'attribution_quote':quote,'kind':'personal','date':None,'date_quote':None}]
            subject={'id':'p','name':'Alice Example','aliases':[],'entity_type':'person','organization_id':'test','roles':[]}
            page={'url':'https://example.gov/a','text':quote,'verified_via':'exact_normalized_page_text'}
            first=archive.process_document(root,page,[subject],{},Client())
            self.assertEqual(first['added'],{'p':['s1']})
            second=archive.process_document(root,{**page,'url':'https://example.gov/mirror'},[subject],{},Client())
            self.assertEqual(second['added'],{});self.assertEqual(second['duplicate_excerpts'],1)

    def test_failed_downloads_count_toward_document_limit(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'data').mkdir()
            state={'documents':{f'https://example.gov/{n}':{'url':f'https://example.gov/{n}'} for n in range(5)},'indexes':{}}
            (root/archive.STATE).write_text(json.dumps(state))
            with patch.object(archive.policy_subjects,'load_subjects',return_value=[]),patch.object(archive,'fetch',side_effect=ValueError('unavailable')) as download:
                result=archive.collect(root,{},object(),max_documents=2,discover_sources=False)
            self.assertEqual(download.call_count,2);self.assertEqual(result['checked_documents'],2)
            self.assertEqual(len(result['errors']),2)

    def test_shifted_excerpt_with_substantial_shared_words_is_duplicate(self):
        old={'date':'2026-01-01','text':'AI can improve medical care and public services across the country. We need effective oversight.'}
        new={'date':'2026-01-01','text':'Public officials said AI can improve medical care and public services across the country.'}
        self.assertTrue(archive.duplicate_excerpt(new,[old]))
        self.assertFalse(archive.duplicate_excerpt({**new,'date':'2026-02-01'},[old]))

    def test_malformed_model_response_survives_parse_failure_without_another_call(self):
        with tempfile.TemporaryDirectory() as d:
            client=archive.sources.Client.__new__(archive.sources.Client);client.daily=False
            client.chat=lambda *a,**kw: {'choices':[{'message':{'content':'bad json'}}]}
            cache=Path(d)/'response.json';page={'url':'https://example.gov/a','text':'Artificial intelligence'}
            with self.assertRaises(ValueError):client.extract(page,[],response_cache=cache)
            self.assertTrue(cache.exists())
            client.chat=lambda *a,**kw: self.fail('Repeated paid request')
            with self.assertRaises(ValueError):client.extract(page,[],response_cache=cache)

    def test_fed_speech_author_comes_from_exact_article_element(self):
        url='https://www.federalreserve.gov/newsevents/speech/barr20260714a.htm'
        text='Artificial intelligence can improve public services and help many people throughout the country.'
        html='<nav>'+('Navigation '*1000)+'</nav><div id="article"><p class="speaker"><a>Governor Michael S. Barr</a></p><p>'+text+'</p></div><footer>Other Person</footer>'
        page=archive.page_from_bytes(url,html.encode())
        self.assertNotIn('Navigation',page['text']);self.assertNotIn('Other Person',page['text'])
        subject={'id':'p','name':'Michael S. Barr','aliases':[],'entity_type':'person','organization_id':'fed','roles':[]}
        row={'subject_id':'p','quote':text,'attribution_quote':'Governor Michael S. Barr','attribution_basis':'document_author','kind':'personal','date':None,'date_quote':None}
        valid,rejected=archive.federal.validate_rows(page,[row],[subject],'2026-11-12')
        self.assertEqual(rejected,0);self.assertEqual(len(valid),1)
        valid,rejected=archive.federal.validate_rows({**page,'url':'https://example.gov/a'},[row],[subject],'2026-11-12')
        self.assertEqual(valid,[]);self.assertEqual(rejected,1)

    def test_malformed_chunk_is_not_retried_automatically(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]
            class Client:
                def extract(self,*args,**kw):calls.append(1);raise ValueError('malformed')
            page={'url':'https://example.gov/a','text':'Alice Example discusses artificial intelligence and public services.','verified_via':'exact_normalized_page_text'}
            subject={'id':'p','name':'Alice Example','aliases':[],'entity_type':'person','roles':[]};state={}
            for _ in range(2):
                result=archive.process_document(Path(d),page,[subject],state,Client())
                self.assertEqual(result['status'],'needs_review');self.assertEqual(result['extraction_errors'],1)
            self.assertEqual(len(calls),1)

    def test_pilot_retry_preserves_collection_spend_and_review_reserve(self):
        from scripts import federal_archives as runner
        import llm
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'evidence').mkdir();(root/'evidence/p.json').write_text(json.dumps({'id':'p','statements':[]}))
            spent=[100.0];limits=[]
            def failed_collection(*args,**kw):spent[0]+=0.6;raise RuntimeError('interrupted')
            with patch.object(runner,'PILOT_IDS',['p']),patch.object(llm,'spent',side_effect=lambda provider:spent[0]),patch('scripts.federal_expansion_runner.command',return_value={'spendable_usd':20}),patch.object(archive.sources,'Client',side_effect=lambda root,limit,**kw:limits.append(limit)),patch.object(archive,'collect',side_effect=failed_collection):
                for _ in range(2):
                    with self.assertRaises(RuntimeError):runner.pilot(root)
            self.assertAlmostEqual(limits[0],2);self.assertAlmostEqual(limits[1],1.4)
            saved=json.loads((root/runner.PILOT).read_text())
            self.assertEqual(saved['budget_baseline'],100);self.assertEqual(saved['collection_baseline'],100)
            self.assertAlmostEqual(saved['spent_usd'],1.2)

    def test_offline_cache_check_reuses_completed_source_and_rejects_changed_snapshot(self):
        from scripts import federal_archives as runner
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);subject={'id':'p','name':'Alice Example','aliases':[],'entity_type':'person','roles':[]}
            page={'url':'https://example.gov/a','text':'Alice Example discusses artificial intelligence in government services.','verified_via':'exact_normalized_page_text'}
            class Client:
                def extract(self,*args,**kw):return []
            processed={};archive.process_document(root,page,[subject],processed,Client())
            path=root/archive.RAW/'pages'/f"{archive.sources.digest(page['url'])}.json"
            archive.federal.write(path,page)
            archive.federal.write(root/archive.STATE,{'documents':{page['url']:{'processed':processed}}})
            evidence={'statements':[{'sid':'s1','text':page['text'],'url':page['url'],'source_text_sha256':archive.sources.digest(page['text'])}]}
            archive.federal.write(root/'evidence/p.json',evidence)
            archive.federal.write(root/runner.PILOT,{'ids':['p'],'added':{'p':['s1']},'new_statements':1})
            with patch.object(archive.policy_subjects,'load_subjects',return_value=[subject]):
                result=runner.check_cache(root);self.assertEqual(result['documents'],1);self.assertEqual(result['model_requests'],0)
                self.assertEqual(result['verified_new_excerpts'],1)
                # Unrelated daily documents must not invalidate this pilot check.
                archive.federal.write(root/archive.STATE,{'documents':{page['url']:{'processed':processed},'https://other.gov/a':{'processed':{'status':'complete'}}}})
                self.assertEqual(runner.check_cache(root)['documents'],1)
                for changed in ({'statements':[]},{'statements':evidence['statements']*2}):
                    archive.federal.write(root/'evidence/p.json',changed)
                    with self.assertRaisesRegex(ValueError,'Missing or duplicated'):runner.check_cache(root)
                archive.federal.write(root/'evidence/p.json',evidence)
                broken={**processed,'chunks':{}}
                archive.federal.write(root/archive.STATE,{'documents':{page['url']:{'processed':broken}}})
                with patch.object(archive.federal,'append_evidence',side_effect=AssertionError('Verification cannot write evidence')):
                    with self.assertRaisesRegex(ValueError,'Incomplete source checkpoint'):runner.check_cache(root)
                self.assertEqual(archive.federal.read(root/'evidence/p.json',{}),evidence)
                archive.federal.write(root/archive.STATE,{'documents':{page['url']:{'processed':processed}}})
                archive.federal.write(path,{**page,'text':page['text']+' Changed.'})
                with self.assertRaises(ValueError):runner.check_cache(root)

if __name__=='__main__':unittest.main()
