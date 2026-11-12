import tempfile
import unittest
from pathlib import Path
from scripts import federal_collection_campaign as campaign


class CampaignTests(unittest.TestCase):
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
            page={'url':'https://agency.gov/a','text':'Alice says artificial intelligence needs careful oversight across the economy.'}
            row={'sid':'s2','url':page['url'],'text':page['text'],'source_text_sha256':campaign.archive.sources.digest(page['text']),'origin':'federal_archive','verified':True}
            campaign.write(root/'evidence/p.json',{'statements':[{'sid':'s1'},row]})
            self.assertEqual(campaign.recover_additions(root,audit),{'p':['s2']})
            campaign.write(root/campaign.archive.RAW/'pages'/f"{campaign.archive.sources.digest(page['url'])}.json",page)
            audit['added']={'p':['s2']}
            self.assertEqual(campaign.verify_sources(root,audit)['verified_new_excerpts'],1)
            campaign.write(root/'evidence/p.json',{'statements':[{'sid':'s1'}]})
            with self.assertRaises(ValueError):campaign.verify_sources(root,audit)

    def test_gap_queries_rotate_groups_and_only_select_low_evidence_officials(self):
        subjects=[{'id':str(i),'name':'Official '+str(i),'organization_id':'a' if i<4 else 'b'} for i in range(6)]
        groups=[{'id':'a','organization_ids':['a'],'domains':['a.gov']},{'id':'b','organization_ids':['b'],'domains':['b.gov']}]
        evidence={s['id']:[] for s in subjects};evidence['0']=[{}]*10
        queries=campaign.gap_queries(subjects,evidence,groups,{})
        self.assertEqual([q['group'] for q in queries[:2]],['a','b'])
        self.assertNotIn('0',[pid for q in queries for pid in q['ids']])

