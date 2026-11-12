import json
import tempfile
import unittest
from pathlib import Path
from scripts.daily.federal_sources import Client


class SearchCacheTests(unittest.TestCase):
    def client(self,root,response):
        client=Client.__new__(Client);client.root=root;client.model='test';client.daily=False
        calls=[]
        def chat(*args,**kwargs):calls.append(1);return response
        client.chat=chat
        return client,calls

    def test_empty_and_positive_search_results_reuse_complete_request(self):
        for pages in ([],[{'url_citation':{'url':'https://agency.gov/a','content':'Source text','title':'AI speech'}}]):
            with self.subTest(pages=bool(pages)),tempfile.TemporaryDirectory() as d:
                response={'choices':[{'message':{'annotations':pages}}],'usage':{'server_tool_use_details':{'web_search_requests':1}}}
                client,calls=self.client(Path(d),response)
                first=client.search('Alice AI',['agency.gov'],'2023-01-01',until='2026-11-12')
                self.assertEqual(first,client.search('Alice AI',['agency.gov'],'2023-01-01',until='2026-11-12'))
                self.assertEqual(len(calls),1)
                client.search('Alice AI',['agency.gov'],'2023-01-01',until='2026-11-13')
                self.assertEqual(len(calls),2)
                client.model='new-model';client.search('Alice AI',['agency.gov'],'2023-01-01',until='2026-11-13')
                self.assertEqual(len(calls),3)

    def test_malformed_response_is_saved_before_parse_and_not_paid_again(self):
        with tempfile.TemporaryDirectory() as d:
            client,calls=self.client(Path(d),{'invalid':'response'})
            for _ in range(2):
                with self.assertRaises(KeyError):client.search('AI',['agency.gov'],'2023-01-01',until='2026-11-12')
            self.assertEqual(len(calls),1)

