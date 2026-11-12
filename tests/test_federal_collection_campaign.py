import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import federal_collection_campaign as campaign


class CampaignTests(unittest.TestCase):
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
            page={'url':'https://agency.gov/a','text':'Alice says artificial intelligence needs careful oversight across the economy.','verified_via':'exact_normalized_page_text'}
            subject={'id':'p','name':'Alice','aliases':[],'entity_type':'person','organization_id':'agency','roles':[]}
            row={'sid':'s2','url':page['url'],'text':page['text'],'context':page['text'],'source_text_sha256':campaign.archive.sources.digest(page['text']),'origin':'federal_archive','verified':True,
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

