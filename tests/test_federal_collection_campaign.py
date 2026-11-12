import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import federal_collection_campaign as campaign


class CampaignTests(unittest.TestCase):
    def test_fixed_x_catchup_keeps_original_budget_and_unfinished_work_pending(self):
        from scripts import federal_x
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);audit={'x_baseline':90,'limits':{'x_limit_usd':5}}
            window={'since':'2026-11-10','until':'2026-11-12'}
            calls=[]
            def collect(*args,**kwargs):
                calls.append(kwargs)
                return {'pending_windows':3 if kwargs.get('dry') else 1,'accounts':3}
            with patch.object(federal_x,'collect',side_effect=collect):
                report=campaign.x_catchup(root,audit,window,['p'],93.5)
            self.assertEqual(report['status'],'pending')
            self.assertEqual(calls[1]['max_cost'],.5)
            self.assertEqual(calls[1]['since'],window['since'])
            self.assertEqual(calls[1]['until'],window['until'])
            self.assertEqual(calls[1]['ids'],['p'])
            self.assertEqual(audit['x_baseline'],90)
            with patch.object(federal_x,'collect',return_value={'pending_windows':0}) as collect:
                self.assertEqual(campaign.x_catchup(root,audit,window,['p'],94.5)['status'],'complete')
                self.assertEqual(collect.call_count,1)
            with patch.object(federal_x,'collect',return_value={'pending_windows':3}) as collect:
                self.assertEqual(campaign.x_catchup(root,audit,window,['p'],94.5)['status'],'pending')
                self.assertEqual(collect.call_count,1)

    def test_catchup_window_survives_failure_and_config_removal(self):
        import llm
        from scripts import federal_x
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);subject={'id':'p','name':'Alice','entity_type':'person','branch':'executive'}
            window={'since':'2026-11-10','until':'2026-11-12'}
            config={'limit_usd':100,'trial_limit_usd':3,'collection_limit_usd':20,'x_limit_usd':5,'x_catchup':window}
            campaign.write(root/campaign.CONFIG,config)
            campaign.write(root/'evidence/p.json',{'statements':[]})
            ledger=root/'data/cost_ledger.jsonl';ledger.parent.mkdir(parents=True);ledger.write_text('')
            audit=campaign.initialize(root,config,[subject],{'p':[]},400,90,0)
            audit['phases']={'trial':{'status':'complete'},'expand':{'archive_selection_version':2,
                'archives_finished':True,'archive_batches':[],'gap_search_finished':True,'x_finished':True}}
            campaign.write(root/campaign.PATH,audit)
            with patch.object(campaign.analysis,'inputs',return_value=([subject],{'p':[]})), \
                 patch.object(campaign,'command',return_value={'spendable_usd':100}), \
                 patch.object(llm,'spent',side_effect=lambda p:400 if p=='openrouter' else 90), \
                 patch.object(llm,'LEDGER',ledger), \
                 patch.object(federal_x,'registry',return_value=({'accounts':[{'subject_id':'p'}]},{})):
                with patch.object(campaign,'x_catchup',side_effect=RuntimeError('Temporary failure')):
                    with self.assertRaisesRegex(RuntimeError,'Temporary failure'):campaign.run(root,'expand')
                saved=campaign.read(root/campaign.PATH)
                self.assertEqual(saved['phases']['expand']['x_catchup']['window'],window)
                self.assertEqual(saved['phases']['expand']['x_catchup']['status'],'pending')
                config.pop('x_catchup');campaign.write(root/campaign.CONFIG,config)
                with patch.object(campaign,'x_catchup',return_value={'window':window,'status':'pending'}) as collect:
                    with self.assertRaisesRegex(ValueError,'collection remains pending'):campaign.run(root,'expand')
                    self.assertEqual(collect.call_args.args[2],window)
                config['x_catchup']={**window,'until':'2026-11-13'};campaign.write(root/campaign.CONFIG,config)
                with patch.object(campaign,'x_catchup') as collect:
                    with self.assertRaisesRegex(ValueError,'cannot move'):campaign.run(root,'expand')
                    collect.assert_not_called()

    def test_source_recovery_failure_saves_pending_before_paid_work(self):
        import llm
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);subject={'id':'p','name':'Alice','entity_type':'person','branch':'executive'}
            config={'limit_usd':100,'trial_limit_usd':3,'collection_limit_usd':20,'x_limit_usd':5}
            campaign.write(root/campaign.CONFIG,config)
            campaign.write(root/'evidence/p.json',{'statements':[{'sid':'s1','verified':True}]})
            ledger=root/'data/cost_ledger.jsonl';ledger.parent.mkdir(parents=True);ledger.write_text('')
            audit=campaign.initialize(root,config,[subject],{'p':[]},400,90,0)
            audit.update(status='complete',phases={'trial':{'status':'complete'},'expand':{'status':'complete'}})
            campaign.write(root/campaign.PATH,audit)
            with patch.object(campaign.analysis,'inputs',return_value=([subject],{'p':[]})), \
                 patch.object(campaign,'command',return_value={'spendable_usd':100}), \
                 patch.object(llm,'spent',side_effect=lambda p:400 if p=='openrouter' else 90), \
                 patch.object(llm,'LEDGER',ledger), \
                 patch.object(campaign,'hydrate_sources',side_effect=ValueError('Source text changed')), \
                 patch.object(campaign.models,'run') as models, \
                 patch.object(campaign.archive.sources,'Client') as extraction:
                with self.assertRaisesRegex(ValueError,'Source text changed'):campaign.run(root,'expand')
                models.assert_not_called();extraction.assert_not_called()
            saved=campaign.read(root/campaign.PATH)
            self.assertEqual(saved['status'],'pending')
            self.assertEqual(saved['phases']['expand']['status'],'pending')
            self.assertIn('Source text changed',saved['phases']['expand']['error'])
            self.assertEqual(saved['added'],{'p':['s1']})
            self.assertEqual(saved['baseline'],400)

    def test_missing_government_snapshot_restores_only_identical_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);archive=campaign.archive;url='https://example.gov/speech'
            text='Alice Example said that artificial intelligence must improve public services and protect privacy. '+('Source context. '*5)
            row={'sid':'s1','url':url,'source_type':'official_statement','source_text_sha256':archive.sources.digest(text.strip())}
            campaign.write(root/'evidence/p.json',{'statements':[row]})
            audit={'added':{'p':['s1']}}
            path=root/archive.RAW/'pages'/f'{archive.sources.digest(url)}.json'
            with patch.object(archive,'fetch',return_value=(text.encode(),url)) as fetch:
                result=campaign.hydrate_sources(root,audit)
                self.assertEqual(result['restored_sources'],1)
                self.assertEqual(campaign.read(path)['text'],text.strip())
                campaign.hydrate_sources(root,audit)
                self.assertEqual(fetch.call_count,1)

    def test_snapshot_recovery_rejects_changed_text_redirects_and_nonofficial_hosts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);archive=campaign.archive
            text='Alice Example said that artificial intelligence must improve public services and protect privacy. '+('Source context. '*5)
            for url,final,body in [('https://example.gov/speech','https://example.gov/speech',text+' Changed.'),
                                   ('https://example.gov/speech','https://example.gov/other',text),
                                   ('https://news.example/speech','https://news.example/speech',text)]:
                row={'sid':'s1','url':url,'source_type':'official_statement','source_text_sha256':archive.sources.digest(text.strip())}
                campaign.write(root/'evidence/p.json',{'statements':[row]})
                with patch.object(archive,'fetch',return_value=(body.encode(),final)) as fetch:
                    with self.assertRaises(ValueError):campaign.hydrate_sources(root,{'added':{'p':['s1']}})
                    if 'news.example' in url:fetch.assert_not_called()
                path=root/archive.RAW/'pages'/f'{archive.sources.digest(url)}.json'
                self.assertFalse(path.exists())

    def test_reporting_verification_recovers_only_hash_matched_source_bound_context(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);archive=campaign.archive
            subject={'id':'p','name':'Alice Example','entity_type':'person','organization_id':'agency','roles':[]}
            quote='Artificial intelligence must improve public services and protect privacy.'
            context=f'Alice Example said, “{quote}”'
            page={'url':'https://news.example/story','text':context,'verified_via':'exact_normalized_page_text'}
            proposal={'subject_id':'p','quote':quote,'attribution_quote':context,'kind':'personal','date':None,'date_quote':None}
            good,rejected=archive.federal.validate_rows(page,[proposal],[subject],'2026-11-12')
            self.assertEqual(rejected,0)
            row={k:v for k,v in good[0][1].items() if not k.startswith('attribution_span_start') and not k.startswith('attribution_span_end')}
            row['sid']='s1';signature='a'*64
            campaign.write(root/'evidence/p.json',{'statements':[row]})
            campaign.write(root/archive.RAW/'pages'/f"{archive.sources.digest(page['url'])}.json",page)
            campaign.write(root/archive.STATE,{'documents':{page['url']:{'processed':{'signature':signature}}}})
            path=root/archive.RAW/'extractions'/f'{signature}-0.json';campaign.write(path,[proposal])
            audit={'added':{'p':['s1']}}
            with patch.object(campaign.policy_subjects,'load_subjects',return_value=[subject]):
                self.assertEqual(campaign.verify_sources(root,audit)['verified_new_excerpts'],1)
                for changed in [{**proposal,'subject_id':'other'}, {**proposal,'attribution_quote':context+' changed'}]:
                    campaign.write(path,[changed])
                    with self.assertRaises(ValueError):campaign.verify_sources(root,audit)
                campaign.write(path,[proposal]);campaign.write(root/archive.STATE,{'documents':{}})
                with self.assertRaises(ValueError):campaign.verify_sources(root,audit)

    def test_reporting_span_proof_survives_extraction_rotation_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);archive=campaign.archive
            subject={'id':'p','name':'Alice Example','entity_type':'person','organization_id':'agency','roles':[]}
            quote='Artificial intelligence must improve public services and protect privacy.'
            context=f'Alice Example said, “{quote}”'
            page={'url':'https://news.example/story','text':context,'verified_via':'exact_normalized_page_text'}
            proposal={'subject_id':'p','quote':quote,'attribution_quote':context,'kind':'personal','date':None,'date_quote':None}
            row={**archive.federal.validate_rows(page,[proposal],[subject],'2026-11-12')[0][0][1],'sid':'s1'}
            self.assertEqual(row.get('attribution_span_start'),0)
            self.assertEqual(row.get('attribution_span_end'),len(context))
            campaign.write(root/archive.RAW/'pages'/f"{archive.sources.digest(page['url'])}.json",page)
            campaign.write(root/'evidence/p.json',{'statements':[row]})
            campaign.write(root/archive.STATE,{'documents':{page['url']:{'processed':{'signature':'b'*64}}}})
            with patch.object(campaign.policy_subjects,'load_subjects',return_value=[subject]):
                self.assertEqual(campaign.verify_sources(root,{'added':{'p':['s1']}})['verified_new_excerpts'],1)
                for change in [{'attribution_span_start':1},{'attribution_span_start':True},{'attribution_span_end':len(context)+1},{'attribution_span_sha256':'0'*64}]:
                    campaign.write(root/'evidence/p.json',{'statements':[{**row,**change}]})
                    with self.assertRaises(ValueError):campaign.verify_sources(root,{'added':{'p':['s1']}})

    def test_recovered_additions_exclude_unverified_or_withdrawn_records(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            campaign.write(root/'evidence/p.json',{'statements':[
                {'sid':'s1','verified':True}, {'sid':'s2','verified':False},
                {'sid':'s3'}, {'sid':'s4','verified':True}]})
            audit={'ids':['p'],'initial_sids':{'p':['s1']}}
            self.assertEqual(campaign.recover_additions(root,audit),{'p':['s4']})

    def test_profile_review_survives_withdrawal_of_its_last_addition(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            campaign.write(root/'evidence/p.json',{'statements':[{'sid':'s1','verified':False}]})
            audit={'ids':['p'],'initial_sids':{'p':[]},'correction_profile_ids':['p']}
            self.assertEqual(campaign.recover_additions(root,audit),{})
            self.assertEqual(campaign.changed_profiles(root,audit),['p'])
            with self.assertRaises(ValueError):
                campaign.changed_profiles(root,{**audit,'correction_profile_ids':['outside']})

    def test_all_official_x_scope_retries_remaining_history_with_original_allowance(self):
        import llm
        from scripts import federal_x
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            subjects=[{'id':'p','name':'Alice','entity_type':'person','branch':'executive'}]
            evidence={'p':[{'sid':f's{i}'} for i in range(4)]}
            config={'limit_usd':100,'trial_limit_usd':3,'collection_limit_usd':20,'x_limit_usd':5,
                    'x_scope':'all_current_officials'}
            campaign.write(root/campaign.CONFIG,config)
            campaign.write(root/'evidence/p.json',{'statements':evidence['p']})
            ledger=root/'data/cost_ledger.jsonl';ledger.parent.mkdir(parents=True);ledger.write_text('')
            audit=campaign.initialize(root,config,subjects,evidence,400,90,0)
            audit['phases']={'trial':{'status':'complete'},'expand':{
                'archive_selection_version':2,'archives_finished':True,'archive_batches':[],
                'gap_search_finished':True,'queries':{},'x_finished':True,'x':{'pending_windows':0}}}
            campaign.write(root/campaign.PATH,audit)
            accounts={'accounts':[{'subject_id':'p'},{'subject_id':'outside_campaign'}]}
            calls=[]
            def collect(*args,**kwargs):
                calls.append(kwargs)
                return {'pending_windows':1 if kwargs.get('dry') else 0,'accounts':1}
            with patch.object(campaign.analysis,'inputs',return_value=(subjects,evidence)),patch.object(campaign,'command',return_value={'spendable_usd':100}),patch.object(llm,'spent',side_effect=lambda p:401 if p=='openrouter' else 93.5),patch.object(llm,'LEDGER',ledger),patch.object(federal_x,'registry',return_value=(accounts,{})),patch.object(federal_x,'collect',side_effect=collect):
                result=campaign.run(root,'expand')
            self.assertEqual(len(calls),2)
            self.assertEqual(calls[0]['ids'],['p'])
            self.assertEqual(calls[1]['ids'],['p'])
            self.assertEqual(calls[1]['max_cost'],.5)
            self.assertNotIn('until',calls[1])
            self.assertEqual(result['baseline'],400)
            self.assertEqual(result['x_baseline'],90)
            self.assertEqual(result['status'],'complete')
            campaign.write(root/campaign.PATH,audit);calls.clear()
            with patch.object(campaign.analysis,'inputs',return_value=(subjects,evidence)),patch.object(campaign,'command',return_value={'spendable_usd':100}),patch.object(llm,'spent',side_effect=lambda p:401 if p=='openrouter' else 94.5),patch.object(llm,'LEDGER',ledger),patch.object(federal_x,'registry',return_value=(accounts,{})),patch.object(federal_x,'collect',side_effect=collect):
                with self.assertRaisesRegex(ValueError,'collection remains pending'):
                    campaign.run(root,'expand')
            self.assertEqual(len(calls),1)
            saved=campaign.read(root/campaign.PATH)
            self.assertFalse(saved['phases']['expand']['x_finished'])
            self.assertEqual(saved['phases']['expand']['x_plan']['pending_windows'],1)

    def test_recovered_additions_exclude_documented_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);old={'sid':'s1','url':'https://example.gov/speech','text':'A verified quotation about artificial intelligence.','verified':True}
            campaign.write(root/'evidence/p.json',{'statements':[old,{**old,'sid':'s2','duplicate_of':'s1'},{**old,'sid':'s3','text':'A separate verified quotation about artificial intelligence.'}]})
            audit={'ids':['p'],'initial_sids':{'p':['s1']}}
            self.assertEqual(campaign.recover_additions(root,audit),{'p':['s3']})

    def test_fresh_archive_run_discovers_sources_before_speaker_migration(self):
        import llm
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);url='https://example.gov/a'
            subjects=[{'id':'p','name':'Alice Example','organization_id':'a','entity_type':'person','branch':'executive','source_speaker_aliases':[{'source_urls':[url]}]}];evidence={'p':[]}
            config={'limit_usd':100,'trial_limit_usd':3,'collection_limit_usd':20,'x_limit_usd':5,'archive_documents':1,'archive_excerpt_limit':100}
            campaign.write(root/campaign.CONFIG,config);campaign.write(root/'evidence/p.json',{'statements':[]})
            ledger=root/'data/cost_ledger.jsonl';ledger.parent.mkdir(parents=True);ledger.write_text('')
            audit=campaign.initialize(root,config,subjects,evidence,400,90,0)
            audit['phases']={'trial':{'status':'complete'},'expand':{'archive_selection_version':2,'gap_search_finished':True,'x_finished':True,'queries':{},'archive_batches':[]}}
            campaign.write(root/campaign.PATH,audit);campaign.write(root/campaign.archive.STATE,{'documents':{url:{}}})
            def finish(root,*args,**kwargs):
                campaign.write(root/campaign.archive.STATE,{'documents':{url:{'processed':{'status':'complete'}}}})
                return {'checked_documents':1,'status':'complete','document_outcomes':[{'url':url}],'discovered':kwargs['discover_sources']}
            with patch.object(campaign.analysis,'inputs',return_value=(subjects,evidence)),patch.object(campaign,'command',return_value={'spendable_usd':100}),patch.object(llm,'spent',side_effect=lambda p:400 if p=='openrouter' else 90),patch.object(llm,'LEDGER',ledger),patch.object(campaign.archive.sources,'Client'),patch.object(campaign.archive,'collect',side_effect=finish):
                result=campaign.run(root,'expand')
            self.assertTrue(result['phases']['expand']['archive_batches'][0]['discovered'])

    def test_archive_retry_finishes_after_document_quota_is_reached(self):
        import llm
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);subjects=[{'id':'p','name':'Alice Example','organization_id':'a','entity_type':'person','branch':'executive'}];evidence={'p':[]}
            config={'limit_usd':100,'trial_limit_usd':3,'collection_limit_usd':20,'x_limit_usd':5,'archive_documents':1,'archive_excerpt_limit':100}
            campaign.write(root/campaign.CONFIG,config);campaign.write(root/'evidence/p.json',{'statements':[]})
            ledger=root/'data/cost_ledger.jsonl';ledger.parent.mkdir(parents=True);ledger.write_text('')
            audit=campaign.initialize(root,config,subjects,evidence,400,90,0)
            audit['phases']={'trial':{'status':'complete'},'expand':{'archive_selection_version':2,'gap_search_finished':True,'x_finished':True,'queries':{},'pending_archive_urls':['https://example.gov/a'],'archive_batches':[{'checked_documents':1,'document_outcomes':[{'url':'https://example.gov/a'}]}]}}
            campaign.write(root/campaign.PATH,audit)
            campaign.write(root/campaign.archive.STATE,{'documents':{'https://example.gov/a':{'processed':{'status':'pending'}}}})
            def finish(root,*args,**kwargs):
                campaign.write(root/campaign.archive.STATE,{'documents':{'https://example.gov/a':{'processed':{'status':'complete'}}}})
                return {'checked_documents':1,'status':'complete','document_outcomes':[{'url':'https://example.gov/a'}]}
            with patch.object(campaign.analysis,'inputs',return_value=(subjects,evidence)),patch.object(campaign,'command',return_value={'spendable_usd':100}),patch.object(llm,'spent',side_effect=lambda p:400 if p=='openrouter' else 90),patch.object(llm,'LEDGER',ledger),patch.object(campaign.archive.sources,'Client'),patch.object(campaign.archive,'collect',side_effect=finish):
                result=campaign.run(root,'expand')
            self.assertEqual(result['status'],'complete');self.assertEqual(result['phases']['expand']['pending_archive_urls'],[])
            self.assertEqual(result['baseline'],400)

    def test_pending_source_detection_includes_unattempted_gap_documents(self):
        state={'documents':{'a':{'processed':{'status':'pending'}},'b':{'processed':{'status':'complete'}},
                            'c':{'error':'HTTPStatusError'},'d':{'error':'BudgetExceeded'}}}
        self.assertEqual(campaign.pending_sources(state,['a','b','c','d','e']),['a','d','e'])

    def test_failed_gap_search_keeps_campaign_pending_and_retryable(self):
        import llm
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);subjects=[{'id':'p','name':'Alice Example','organization_id':'a','entity_type':'person','branch':'executive'}];evidence={'p':[]}
            config={'limit_usd':100,'trial_limit_usd':3,'collection_limit_usd':20,'x_limit_usd':5,'gap_query_limit':10,'total_excerpt_limit':2500}
            campaign.write(root/campaign.CONFIG,config)
            campaign.write(root/'config/federal_sources.json',{'groups':[{'id':'a','organization_ids':['a'],'domains':['example.gov']}]})
            campaign.write(root/'evidence/p.json',{'statements':[]})
            ledger=root/'data/cost_ledger.jsonl';ledger.parent.mkdir(parents=True,exist_ok=True);ledger.write_text('')
            audit=campaign.initialize(root,config,subjects,evidence,400,90,0)
            audit['phases']={'trial':{'status':'complete'},'expand':{'archive_selection_version':2,'archives_finished':True,'x_finished':True,'queries':{},'archive_batches':[]}}
            campaign.write(root/campaign.PATH,audit)
            class Broken:
                def search(self,*args,**kwargs):raise RuntimeError('Temporary provider failure')
            with patch.object(campaign.analysis,'inputs',return_value=(subjects,evidence)),patch.object(campaign,'command',return_value={'spendable_usd':100}),patch.object(llm,'spent',side_effect=lambda p:400 if p=='openrouter' else 90),patch.object(llm,'LEDGER',ledger),patch.object(campaign.archive.sources,'Client',return_value=Broken()):
                with self.assertRaisesRegex(ValueError,'collection remains pending'):campaign.run(root,'expand')
            saved=campaign.read(root/campaign.PATH)
            self.assertEqual(saved['status'],'pending');self.assertFalse(saved['phases']['expand']['gap_search_finished'])

    def test_daily_and_campaign_restore_the_same_latest_cache_prefix(self):
        import yaml
        root=Path(__file__).resolve().parents[1];prefixes=[]
        for file in ['daily.yml','federal-collection.yml']:
            config=yaml.safe_load((root/'.github/workflows'/file).read_text())
            steps=next(iter(config['jobs'].values()))['steps']
            cache=next(s for s in steps if s.get('id') in ('cache','archives'))
            prefixes.append(cache['with']['restore-keys'].splitlines()[0])
        self.assertEqual(prefixes,['federal-shared-v2-']*2)

    def test_resume_keeps_original_budget_and_trial_cannot_use_expansion_allowance(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);subjects=[{'id':'p','entity_type':'person','branch':'executive'}];evidence={'p':[{'sid':'s1'}]}
            config={'limit_usd':100,'trial_limit_usd':3,'collection_limit_usd':20,'x_limit_usd':5}
            first=campaign.initialize(root,config,subjects,evidence,400,90,12)
            second=campaign.initialize(root,config,subjects,evidence,402,91,20)
            self.assertEqual(first['baseline'],second['baseline'])
            self.assertEqual(campaign.allowance(second,'trial',402,100),1)
            self.assertEqual(campaign.allowance(second,'expand',402,100),98)
            self.assertEqual(campaign.allowance(second,'expand',402,.5),.5)
            with self.assertRaises(ValueError):campaign.allowance(second,'expand',399,100)

    def test_recover_additions_and_source_verification_detect_missing_or_changed_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            audit={'initial_sids':{'p':['s1']},'ids':['p']}
            quote='Artificial intelligence needs careful oversight across the whole economy.'
            page={'url':'https://agency.gov/a','text':f'Alice said, “{quote}”','verified_via':'exact_normalized_page_text'}
            subject={'id':'p','name':'Alice','aliases':[],'entity_type':'person','organization_id':'agency','roles':[]}
            row={'sid':'s2','url':page['url'],'text':quote,'context':page['text'],'source_text_sha256':campaign.archive.sources.digest(page['text']),'origin':'federal_archive','verified':True,
                 'attribution':{'speaker':'Alice','kind':'personal','organization_id':'agency','basis':'local_span'},'date':None,'date_quote':None}
            campaign.write(root/'evidence/p.json',{'statements':[{'sid':'s1'},row]})
            self.assertEqual(campaign.recover_additions(root,audit),{'p':['s2']})
            campaign.write(root/campaign.archive.RAW/'pages'/f"{campaign.archive.sources.digest(page['url'])}.json",page)
            audit['added']={'p':['s2']}
            with patch.object(campaign.policy_subjects,'load_subjects',return_value=[subject]):
                self.assertEqual(campaign.verify_sources(root,audit)['verified_new_excerpts'],1)
                campaign.write(root/'evidence/p.json',{'statements':[{'sid':'s1'},{**row,'context':'Bob said these words.'}]})
                with self.assertRaisesRegex(ValueError,'attribution or date'):campaign.verify_sources(root,audit)
            campaign.write(root/'evidence/p.json',{'statements':[{'sid':'s1'}]})
            with self.assertRaises(ValueError):campaign.verify_sources(root,audit)

    def test_gap_queries_rotate_groups_and_only_select_low_evidence_officials(self):
        subjects=[{'id':str(i),'name':'Official '+str(i),'organization_id':'a' if i<4 else 'b'} for i in range(6)]
        groups=[{'id':'a','organization_ids':['a'],'domains':['a.gov']},{'id':'b','organization_ids':['b'],'domains':['b.gov']}]
        evidence={s['id']:[] for s in subjects};evidence['0']=[{}]*10
        queries=campaign.gap_queries(subjects,evidence,groups,{})
        self.assertEqual([q['group'] for q in queries[:2]],['a','b'])
        self.assertNotIn('0',[pid for q in queries for pid in q['ids']])

