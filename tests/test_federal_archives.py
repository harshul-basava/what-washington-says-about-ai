import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import federal_archives as archive

class ArchiveTests(unittest.TestCase):
    def test_fdic_metadata_migration_preserves_changed_source_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);url='https://www.fdic.gov/news/speeches/2026/example'
            html=b'<div class="field--name-field-speaker-information"><div class="speaker field__item">Chairman Travis Hill</div></div><p>Artificial intelligence can improve public services and help many people throughout the country, while appropriate oversight protects consumers.</p>'
            page=archive.page_from_bytes(url,html);page.pop('fdic_speaker_version',None);page.pop('structured_author',None)
            subject={'id':'p','name':'Travis Hill','branch':'executive','entity_type':'person','organization_id':'fdic','roles':[]}
            cache=root/archive.RAW/'pages'/f'{archive.sources.digest(url)}.json'
            archive.federal.write(cache,page)
            archive.federal.write(root/archive.STATE,{'documents':{url:{'url':url,'fetched_on':'2000-01-01'}},'indexes':{}})
            class Client:
                def extract(self,*args,**kwargs):raise AssertionError('Changed source must not trigger paid extraction')
            with patch.object(archive.policy_subjects,'load_subjects',return_value=[subject]),patch.object(archive,'fetch',return_value=(b'<nav>Changed navigation</nav>'+html,url)):
                result=archive.collect(root,{},Client(),discover_sources=False)
            self.assertEqual(archive.federal.read(cache,{}),page)
            self.assertEqual(result['model_requests'],0)
            self.assertEqual(result['errors'][0]['error'],'SourceSnapshotChanged')

    def test_old_fdic_snapshot_refreshes_once_for_speaker_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);url='https://www.fdic.gov/news/speeches/2026/example'
            html=b'<div class="field--name-field-speaker-information"><div class="speaker field__item">Chairman Travis Hill</div></div><p>Artificial intelligence can improve public services and help many people throughout the country, while appropriate oversight protects consumers.</p>'
            page=archive.page_from_bytes(url,html);page.pop('fdic_speaker_version',None);page.pop('structured_author',None)
            subject={'id':'p','name':'Travis Hill','branch':'executive','entity_type':'person','organization_id':'fdic','roles':[]}
            archive.federal.write(root/archive.RAW/'pages'/f'{archive.sources.digest(url)}.json',page)
            archive.federal.write(root/archive.STATE,{'documents':{url:{'url':url,'fetched_on':archive.federal.today()}},'indexes':{}})
            class Client:
                def extract(self,page,subjects,**kwargs):
                    self.header=page['structured_author']['header'];return []
            client=Client()
            with patch.object(archive.policy_subjects,'load_subjects',return_value=[subject]),patch.object(archive,'fetch',return_value=(html,url)) as fetch:
                archive.collect(root,{},client,discover_sources=False)
                archive.collect(root,{},client,discover_sources=False)
            self.assertEqual(fetch.call_count,1)
            self.assertEqual(client.header,'Chairman Travis Hill')

    def test_fdic_speech_requires_its_single_explicit_speaker_field(self):
        url='https://www.fdic.gov/news/speeches/2026/example'
        quote='Artificial intelligence can improve public services and help many people throughout the country.'
        subject={'id':'p','name':'Travis Hill','aliases':[],'entity_type':'person','organization_id':'fdic','roles':[]}
        speaker='<div class="field--name-field-speaker-information"><div class="speaker field__item">Chairman <span>Travis Hill</span></div></div>'
        html='<nav>Other Person</nav>'+speaker+'<p>'+quote+'</p>'
        row={'subject_id':'p','quote':quote,'attribution_quote':'Chairman Travis Hill','attribution_basis':'document_author','kind':'personal','date':None,'date_quote':None}
        page=archive.page_from_bytes(url,html.encode())
        self.assertEqual(len(archive.federal.validate_rows(page,[row],[subject],'2026-11-12')[0]),1)
        for bad in [archive.page_from_bytes('https://example.gov/news/speeches/2026/example',html.encode()),
                    archive.page_from_bytes('https://www.fdic.gov/news/speeches/2026',html.encode()),
                    archive.page_from_bytes(url,html.replace('field--name-field-speaker-information','footer').encode()),
                    archive.page_from_bytes(url,html.replace('speaker field__item','unrelated').encode()),
                    archive.page_from_bytes(url,(html+speaker).encode()),
                    archive.page_from_bytes(url,html.replace('</div></div>','</div><div class="speaker field__item">Other Person</div></div>').encode())]:
            self.assertEqual(archive.federal.validate_rows(bad,[row],[subject],'2026-11-12'),([],1))

    def test_house_witness_http_links_resolve_to_exact_https_documents(self):
        source={'url':'https://docs.house.gov/Committee/Calendar/ByEvent.aspx?EventID=119184',
                'domains':['docs.house.gov'],'pattern':r'/meetings/.*-Wstate-.*\.pdf$'}
        path='/meetings/AS/AS35/20260514/119184/HHRG-119-AS35-Wstate-StanleyC-20260514.pdf'
        html=f'<a href="http://docs.house.gov{path}">Statement</a>'
        self.assertEqual(archive.archive_links(html,source),[{'url':'https://docs.house.gov'+path,'title':'Statement'}])
        meeting=path.replace('HHRG-','HMTG-')
        self.assertEqual(archive.archive_links(html.replace(path,meeting),source),
                         [{'url':'https://docs.house.gov'+meeting,'title':'Statement'}])
        for bad in ('http://other.house.gov'+path,'http://docs.house.gov:8080'+path,
                    'http://user@docs.house.gov'+path,'http://docs.house.gov'+path+'?download=1'):
            self.assertEqual(archive.archive_links(f'<a href="{bad}">Statement</a>',source),[])
        for index in ('https://other.house.gov/Committee/Calendar/ByEvent.aspx?EventID=119184',
                      'https://docs.house.gov/unrelated?EventID=119184'):
            self.assertEqual(archive.archive_links(html,{**source,'url':index}),[])

    def test_reported_extraction_uses_short_contiguous_quotes_without_changing_official_prompt(self):
        client=archive.sources.Client.__new__(archive.sources.Client);client.daily=False;calls=[]
        def chat(messages,*args,**kwargs):
            calls.append(messages)
            return {'choices':[{'message':{'content':'{"statements":[]}'}}]}
        client.chat=chat
        for url in ('https://example.gov/speech','https://news.example/interview'):
            client.extract({'url':url,'text':'Source text'},[])
        self.assertEqual(calls[0][0]['content'],archive.sources.EXTRACTION_PROMPT)
        self.assertIn('25 words in total',calls[1][0]['content'])
        self.assertIn('self-contained',calls[1][0]['content'])

    def test_reported_archive_requires_explicit_index_opt_in_and_matching_domain(self):
        with tempfile.TemporaryDirectory() as d:
            source={'url':'https://news.example/index','domains':['news.example'],'pattern':'/story/'}
            html=b'<a href="/story/ai">AI interview</a><a href="https://other.example/story/ai">Other</a>'
            with patch.object(archive,'fetch',return_value=(html,source['url'])),patch.object(archive.policy_subjects,'load_subjects',return_value=[]):
                state={};archive.discover(Path(d),{'indexes':[source]},[],state,now='2026-11-12')
                self.assertEqual(state['documents'],{})
                source['source_type']='reported_statement'
                archive.discover(Path(d),{'indexes':[source]},[],state,now='2026-11-12')
            self.assertEqual(set(state['documents']),{'https://news.example/story/ai'})
            self.assertNotIn('subject_ids',state['documents']['https://news.example/story/ai'])

    def test_search_only_snapshot_needs_source_proof_without_paid_extraction(self):
        with tempfile.TemporaryDirectory() as d:
            page={'url':'https://example.gov/speech','text':'Alice Example discusses artificial intelligence policy and its impact.',
                  'verified_via':'exact_normalized_search_retrieval'}
            subject={'id':'p','name':'Alice Example','aliases':[],'entity_type':'person','roles':[]}
            class Client:
                def extract(self,*args,**kwargs):raise AssertionError('Search text cannot verify the source')
            state={};result=archive.process_document(Path(d),page,[subject],state,Client())
            self.assertEqual(result['model_requests'],0)
            self.assertEqual(result['added'],{})
            self.assertEqual(state['reason'],'full_source_snapshot_required')

    def test_verified_institution_documents_are_shared_leads_without_person_attribution(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            person={'id':'p','entity_type':'person','organization_id':'agency'}
            institution={'id':'agency','entity_type':'institution','organization_id':'agency'}
            rows=[{'url':'https://example.gov/statement','verified':True},
                  {'url':'https://example.gov/unverified','verified':False},
                  {'url':'https://x.com/agency/status/123','verified':True}]
            archive.federal.write(root/'config/federal_sources.json',{'groups':[{'id':'group','organization_ids':['agency']}]})
            with patch.object(archive.policy_subjects,'load_subjects',return_value=[person,institution]),patch.object(archive.policy_subjects,'load_evidence',side_effect=lambda root,s:rows if s['id']=='agency' else []):
                state={};archive.discover(root,{'indexes':[]},[person],state,now='2026-11-12')
                self.assertEqual(state['documents'],{})
                archive.discover(root,{'indexes':[],'include_institution_sources':True},[person],state,now='2026-11-12')
            self.assertEqual(set(state['documents']),{'https://example.gov/statement'})
            self.assertEqual(state['documents']['https://example.gov/statement']['group'],'group')
            self.assertNotIn('subject_ids',state['documents']['https://example.gov/statement'])

    def test_treasury_public_json_index_supplies_leads_only_with_date_and_url_bounds(self):
        source={'url':'https://home.treasury.gov/news-data/press-releases/2026-2023.json',
                'domains':['home.treasury.gov'],'pattern':r'/news/press-releases/[^/?#]+/?$',
                'format':'treasury_news_json','since':'2025-01-01'}
        rows=[{'url':'/news/press-releases/sb1/','title':'Remarks on AI','date':'2025-03-01'},
              {'url':'/news/press-releases/jy1/','title':'Earlier remarks','date':'2024-03-01'},
              {'url':'https://example.test/news/press-releases/a/','title':'External','date':'2025-03-01'},
              {'url':'/about/','title':'About','date':'2025-03-01'},
              {'url':'/news/press-releases/bad/','title':'Bad date','date':'not a date'}]
        payload=json.dumps({'category':'press-releases','items':rows})
        self.assertEqual(archive.archive_links(payload,source),
                         [{'url':'https://home.treasury.gov/news/press-releases/sb1/','title':'Remarks on AI'}])
        for bad in [payload.replace('"items"','"missing"'), json.dumps({'items':'not a list'}), '{}']:
            with self.assertRaises(ValueError):archive.archive_links(bad,source)
        with self.assertRaises(ValueError):
            archive.archive_links(payload,{**source,'url':'https://example.gov/news-data/press-releases/2026-2023.json'})

    def test_exact_source_duplicate_does_not_depend_on_date_metadata(self):
        old={'url':'https://example.gov/speech','text':'Artificial intelligence must improve public services and protect privacy.','date':None}
        self.assertTrue(archive.duplicate_excerpt({**old,'date':'2026-11-08'},[old]))
        self.assertFalse(archive.duplicate_excerpt({**old,'url':'https://example.gov/other','date':'2026-11-08'},[old]))

    def test_extractor_receives_only_reviewed_speakers_for_its_source(self):
        client=archive.sources.Client.__new__(archive.sources.Client);client.daily=False;payloads=[]
        def chat(messages,*args,**kwargs):
            payloads.append(json.loads(messages[1]['content']))
            return {'choices':[{'message':{'content':'{"statements":[]}'}}]}
        client.chat=chat
        bound={'label':'MR. JONES.','source_urls':['https://example.gov/hearing'],'valid_from':'2025-01-01'}
        other={'label':'DR. JONES.','source_urls':['https://example.gov/other']}
        subject={'id':'p','name':'John Jones','source_speaker_aliases':[bound,other]}
        client.extract({'url':'https://example.gov/hearing','text':'MR. JONES. Artificial intelligence is relevant to this discussion.'},[subject])
        self.assertEqual(payloads[0]['subjects'][0].get('source_speaker_aliases'),[bound])

    def test_speaker_prompt_fix_invalidates_only_sources_with_bound_mappings(self):
        subject={'id':'p','name':'John Jones','source_speaker_aliases':[{'label':'MR. JONES.','source_urls':['https://example.gov/hearing']}]}
        self.assertNotEqual(archive.extraction_signature('source',[subject],'https://example.gov/hearing'),'5fb8db2f517af34cf78282f4bdc052bb9755cbd6d6ccab005a70af3f64a2f64d')
        self.assertEqual(archive.extraction_signature('source',[subject],'https://example.gov/other'),'f46fe2bf42ec1970d004841ca7edf9282df3a932bd30580b1a2deadff6442022')

    def test_name_candidates_preserve_aliases_middle_initials_unicode_and_reviewed_speakers(self):
        subjects=[{'id':'alice','name':'Alice Example','aliases':['A. Example']},
                  {'id':'kosiba','name':'Timothy Kosiba'},
                  {'id':'rene','name':'René Dumas'},
                  {'id':'john','name':'John Jones','source_speaker_aliases':[{'label':'MR. JONES.','source_urls':['https://example.gov/hearing']}]},
                  {'id':'other','name':'Alice Examples'}]
        text='ALİCE B. EXAMPLE and Timothy Kosiba spoke with René Dumas. MR. JONES. I agree.'
        self.assertEqual([s['id'] for s in archive.named_subjects(text,subjects,'https://example.gov/hearing')],['alice','kosiba','rene','john'])
        self.assertEqual([s['id'] for s in archive.named_subjects('A. Example spoke.',subjects,'https://example.gov/other')],['alice'])
        self.assertEqual(archive.named_subjects('MR. JONES. I agree.',subjects,'https://example.gov/other'),[])

    def test_serial_and_parallel_collection_accept_the_same_verified_evidence(self):
        subject={'id':'p','name':'Alice Example','aliases':[],'entity_type':'person','branch':'executive','organization_id':'test','roles':[]}
        quotes=['Alice Example: Artificial intelligence export controls must prevent hostile military organizations from acquiring advanced computing equipment.',
                'Alice Example: Independent AI auditors should inspect frontier laboratories and publish their safety findings before deployment.']
        docs={f'https://example.gov/{i}':{'url':f'https://example.gov/{i}'} for i in range(2)}
        class Client:
            def extract(self,page,*args,**kwargs):
                return [{'subject_id':'p','quote':page['text'].split(': ',1)[1],'attribution_quote':page['text'],'kind':'personal','date':None,'date_quote':None}]
        outputs=[]
        for workers in (1,2):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);archive.federal.write(root/'evidence/p.json',{'id':'p','statements':[]})
                archive.federal.write(root/archive.STATE,{'documents':docs,'indexes':{}})
                def fetch(url,domains):return ('<p>'+quotes[int(url[-1])]+'</p>').encode(),url
                with patch.object(archive.policy_subjects,'load_subjects',return_value=[subject]),patch.object(archive,'fetch',side_effect=fetch):
                    archive.collect(root,{},Client(),discover_sources=False,max_documents=2,fetch_workers=workers,extraction_workers=workers)
                rows=archive.federal.read(root/'evidence/p.json',{})['statements']
                outputs.append(sorted((r['text'],r['url'],r['verified'],r['attribution']['speaker']) for r in rows))
        self.assertEqual(len(outputs[0]),2);self.assertEqual(outputs[0],outputs[1])

    def test_index_pattern_change_rechecks_same_day_and_access_challenge_is_a_gap(self):
        with tempfile.TemporaryDirectory() as d:
            source={'url':'https://example.gov/index','domains':['example.gov'],'pattern':'/old$'}
            state={};config={'indexes':[source]}
            with patch.object(archive,'fetch',return_value=(b'<a href="/new/">AI</a>','https://example.gov/index')),patch.object(archive.policy_subjects,'load_subjects',return_value=[]):
                archive.discover(Path(d),config,[],state,now='2026-11-12')
                source['pattern']='/new/$'
                archive.discover(Path(d),config,[],state,now='2026-11-12')
            self.assertIn('https://example.gov/new/',state['documents'])
            with patch.object(archive,'fetch',return_value=(b'<meta content="5; URL=/index?bm-verify=challenge">','https://example.gov/index')),patch.object(archive.policy_subjects,'load_subjects',return_value=[]):
                archive.discover(Path(d),config,[],state,now='2026-11-13')
            self.assertEqual(state['indexes'][source['url']]['status'],'source_unavailable')

    def test_sec_speaker_requires_exact_single_official_speaker_field(self):
        url='https://www.sec.gov/newsroom/speeches-statements/example'
        quote='Artificial intelligence can improve public services and help many people throughout the country.'
        subject={'id':'p','name':'Paul S. Atkins','aliases':[],'entity_type':'person','organization_id':'sec','roles':[]}
        speaker='<div class="field--name-dynamic-twig-fieldnode-news-speaker"><div><a href="/about/sec-commissioners/paul-s-atkins">Paul S. Atkins, <span>Chairman</span></a></div></div>'
        html='<nav>Other Person</nav>'+speaker+'<p>'+quote+'</p>'
        row={'subject_id':'p','quote':quote,'attribution_quote':'Paul S. Atkins, Chairman','attribution_basis':'document_author','kind':'personal','date':None,'date_quote':None}
        page=archive.page_from_bytes(url,html.encode())
        valid,rejected=archive.federal.validate_rows(page,[row],[subject],'2026-11-12')
        self.assertEqual((len(valid),rejected),(1,0))
        for bad in [archive.page_from_bytes('https://example.gov/a',html.encode()),
                    archive.page_from_bytes(url,html.replace('field--name-dynamic-twig-fieldnode-news-speaker','footer').encode()),
                    archive.page_from_bytes(url,(html+speaker).encode())]:
            self.assertEqual(archive.federal.validate_rows(bad,[row],[subject],'2026-11-12'),([],1))

    def test_selected_official_sources_precede_unrelated_inventory_without_dropping_it(self):
        docs=[{'url':'https://a.gov/1','group':'a','title':'AI'},
              {'url':'https://b.gov/1','group':'b','title':'AI','subject_ids':['p']},
              {'url':'https://www.sec.gov/1','group':'sec','title':'AI'}]
        ordered=archive.fair_documents(docs,preferred_ids={'p'},preferred_domains=['sec.gov'])
        self.assertEqual([d['url'] for d in ordered],['https://b.gov/1','https://www.sec.gov/1','https://a.gov/1'])

    def test_changed_extractor_invalidates_an_empty_result(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]
            class Client:
                model='first'
                def extract(self,*args,**kwargs):calls.append(self.model);return []
            client=Client();state={}
            page={'url':'https://example.gov/a','text':'Alice Example says artificial intelligence could improve public services.'}
            subject={'id':'p','name':'Alice Example','aliases':[],'entity_type':'person','roles':[]}
            archive.process_document(Path(d),page,[subject],state,client)
            client.model='second';archive.process_document(Path(d),page,[subject],state,client)
            self.assertEqual(calls,['first','second'])

    def test_archive_indexes_download_concurrently_and_save_empty_results(self):
        with tempfile.TemporaryDirectory() as d:
            counts={'active':0,'peak':0};lock=threading.Lock()
            def fetch(url,domains):
                with lock:counts['active']+=1;counts['peak']=max(counts['peak'],counts['active'])
                time.sleep(.02)
                with lock:counts['active']-=1
                return b'<html></html>',url
            config={'index_workers':2,'indexes':[{'url':f'https://example.gov/{i}','domains':['example.gov'],'pattern':'/speech/'} for i in range(2)]}
            state={}
            with patch.object(archive,'fetch',side_effect=fetch) as mocked,patch.object(archive.policy_subjects,'load_subjects',return_value=[]):
                archive.discover(Path(d),config,[],state,now='2026-11-12')
                archive.discover(Path(d),config,[],state,now='2026-11-12')
            self.assertEqual(counts['peak'],2);self.assertEqual(mocked.call_count,2)
            self.assertEqual(len(state['indexes']),2)

    def test_spaced_super_intelligence_rechecks_old_empty_chunk_without_repeating_positive_chunks(self):
        import re
        with tempfile.TemporaryDirectory() as d:
            page={'url':'https://example.gov/a','text':'Alice Example says super intelligence requires careful oversight for public benefit.'}
            subject={'id':'p','name':'Alice Example','aliases':[],'entity_type':'person','roles':[]}
            state={};calls=[]
            class Client:
                def extract(self,*args,**kwargs):calls.append(1);return []
            with patch.object(archive,'AI',re.compile('artificial intelligence')):
                archive.process_document(Path(d),page,[subject],state,Client())
            archive.process_document(Path(d),page,[subject],state,Client())
            archive.process_document(Path(d),page,[subject],state,Client())
            self.assertEqual(len(calls),1)

    def test_fair_document_queue_rotates_across_agencies(self):
        docs=[{'url':f'https://a.gov/{i}','group':'a','title':'AI'} for i in range(4)]
        docs.append({'url':'https://b.gov/1','group':'b','title':'AI'})
        ordered=archive.fair_documents(docs)
        self.assertEqual([d['group'] for d in ordered[:2]],['a','b'])

    def test_parallel_collection_preserves_shared_profile_and_global_chunk_limit(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);subject={'id':'p','name':'Alice Example','aliases':[],'entity_type':'person','branch':'executive','organization_id':'test','roles':[]}
            docs={f'https://example.gov/{i}':{'url':f'https://example.gov/{i}'} for i in range(12)}
            archive.federal.write(root/'evidence/p.json',{'id':'p','statements':[]})
            archive.federal.write(root/archive.STATE,{'documents':docs,'indexes':{}})
            counter={'active':0,'peak':0,'calls':0};lock=threading.Lock();barrier=threading.Barrier(8)
            class Client:
                def extract(self,page,*args,**kwargs):
                    with lock:
                        counter['active']+=1;counter['calls']+=1;counter['peak']=max(counter['peak'],counter['active'])
                    barrier.wait(timeout=3)
                    with lock:counter['active']-=1
                    return [{'subject_id':'p','quote':page['text'].split(': ',1)[1],'attribution_quote':page['text'],'kind':'personal','date':None,'date_quote':None}]
            def page(url,data,title):
                i=url.rsplit('/',1)[-1]
                return {'url':url,'text':f'Alice Example: artificial intelligence improves service {i} through distinct new capabilities for society.', 'verified_via':'exact_normalized_page_text'}
            with patch.object(archive.policy_subjects,'load_subjects',return_value=[subject]),patch.object(archive,'fetch',side_effect=lambda u,d:(b'data',u)),patch.object(archive,'page_from_bytes',side_effect=page),patch.object(archive,'duplicate_excerpt',return_value=False):
                report=archive.collect(root,{},Client(),discover_sources=False,max_documents=12,max_chunks=8,fetch_workers=8,extraction_workers=8)
            self.assertEqual(counter['calls'],8);self.assertEqual(counter['peak'],8)
            self.assertEqual(report['new_statements'],8)
            rows=archive.federal.read(root/'evidence/p.json',{})['statements']
            self.assertEqual({s['sid'] for s in rows},{f's{i}' for i in range(1,9)})
            self.assertEqual(report['chunks_checked'],8)

    def test_completed_download_slot_starts_next_document_before_slow_peer_finishes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);third_started=threading.Event();overlap=[]
            docs={f'https://example.gov/{i}':{'url':f'https://example.gov/{i}'} for i in range(3)}
            archive.federal.write(root/archive.STATE,{'documents':docs,'indexes':{}})
            def fetch(url,domains):
                if url.endswith('/0'):overlap.append(third_started.wait(timeout=1))
                if url.endswith('/2'):third_started.set()
                return b'data',url
            def page(url,data,title):
                return {'url':url,'text':'A public document without a named roster official.',
                        'verified_via':'exact_normalized_page_text'}
            with patch.object(archive.policy_subjects,'load_subjects',return_value=[]),patch.object(archive,'fetch',side_effect=fetch),patch.object(archive,'page_from_bytes',side_effect=page):
                report=archive.collect(root,{},object(),discover_sources=False,max_documents=3,fetch_workers=2)
            self.assertEqual(overlap,[True])
            self.assertEqual(report['checked_documents'],3)

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
                def extract(self,*args,**kw):raise AssertionError('Do not pay for a speaker that cannot pass the existing verifier')
            subject={'id':'p','name':'Alice Example','aliases':[],'entity_type':'person','organization_id':'test','roles':[]}
            page={'url':'https://www.govinfo.gov/content/pkg/CHRG-1/html/CHRG-1.htm','text':quote,'verified_via':'exact_normalized_page_text'}
            result=archive.process_document(Path(d),page,[subject],{},Client())
            self.assertEqual(result['status'],'needs_review');self.assertEqual(result['added'],{})

    def test_exact_verified_excerpt_is_added_once_and_partial_overlap_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'evidence').mkdir();(root/'evidence/p.json').write_text(json.dumps({'id':'p','statements':[]}))
            quote='Artificial intelligence will improve public services across the whole country.'
            context=f'Alice Example said, “{quote}”'
            class Client:
                def extract(self,*args,**kw):return [{'subject_id':'p','quote':quote,'attribution_quote':context,'kind':'personal','date':None,'date_quote':None}]
            subject={'id':'p','name':'Alice Example','aliases':[],'entity_type':'person','organization_id':'test','roles':[]}
            page={'url':'https://example.gov/a','text':context,'verified_via':'exact_normalized_page_text'}
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
