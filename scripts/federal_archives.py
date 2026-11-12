"""Discover official archives or run the fixed-budget collection pilot."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts/daily')]
import federal_archives as archive
import federal
import policy_subjects

PILOT='data/federal_archive_pilot.json'
PILOT_IDS=['exec_michelle_w_bowman','exec_michael_s_barr','exec_christopher_j_waller',
           'exec_philip_n_jefferson','exec_lisa_d_cook','exec_jerome_h_powell',
           'exec_lutnick','exec_kratsios','exec_klein']


def pilot(root):
    import llm
    from scripts.federal_expansion_runner import command, review_cohort
    import federal_analysis_models
    import federal_analysis
    root=Path(root);path=root/PILOT;config=federal.read(root/'config/federal_archives.json',{})
    audit=federal.read(path,{})
    if not audit:
        audit={'version':1,'status':'in_progress','ids':PILOT_IDS,'budget_baseline':llm.spent('openrouter'),
               'limit_usd':10,'collection_limit_usd':2,'created_on':federal.today(),'added':{},'attempts':[]}
        audit['initial_sids']={pid:[s['sid'] for s in federal.read(root/'evidence'/f'{pid}.json',{})['statements']] for pid in audit['ids']}
        federal.write(path,audit)
    credit=command(root,'scripts/openrouter_credit_check.py','--required-credit=0',capture=True)
    start=llm.spent('openrouter');credit_available=credit['spendable_usd']
    def allowance():return min(archive.remaining(audit['budget_baseline'],audit['limit_usd'],llm.spent('openrouter')),
                               archive.remaining(start,credit_available,llm.spent('openrouter')))
    if allowance()<=0:raise ValueError('No remaining pilot credit')
    def recover_additions():
        audit['added']={pid:[s['sid'] for s in federal.read(root/'evidence'/f'{pid}.json',{})['statements']
                            if s['sid'] not in audit['initial_sids'][pid]] for pid in audit['ids']}
        audit['added']={pid:sids for pid,sids in audit['added'].items() if sids}
    attempt={'started_on':federal.today(),'baseline':start};audit['attempts'].append(attempt)
    try:
        if not audit.get('collection_finished'):
            # Collection allowance is cumulative and cannot reset when a run resumes.
            audit.setdefault('collection_baseline',llm.spent('openrouter'))
            federal.write(path,audit)
            available=min(allowance(),archive.remaining(audit['collection_baseline'],audit['collection_limit_usd'],llm.spent('openrouter')))
            if available>0:
                before=llm.spent('openrouter')
                client=archive.sources.Client(root,available,daily=False)
                try:
                    result=archive.collect(root,config,client,ids=audit['ids'],max_documents=70,max_chunks=70)
                    attempt['collection']=result
                    for pid,sids in result['added'].items():audit['added'][pid]=list(dict.fromkeys(audit['added'].get(pid,[])+sids))
                    audit['collection_finished']=result['status']!='provider_limit'
                    if not audit['collection_finished']:raise ValueError('Collection awaits budget or provider recovery')
                finally:audit['collection_spend_usd']=llm.spent('openrouter')-audit['collection_baseline']
            else:audit['collection_finished']=True
            federal.write(path,audit)
        recover_additions()
        ids=sorted(audit['added'])
        if ids:
            attempt['analysis']=federal_analysis_models.run(root,max_cost=allowance(),workers=4,ids=ids)
            if attempt['analysis']['status']!='ok':raise ValueError('Analysis remains pending')
            code=command(root,'scripts/phase3_policies.py','label','--scope','executive','--ids',','.join(ids),'--workers',2,'--max-cost',allowance())
            attempt['policies']=command(root,'scripts/phase3_policies.py','plan','--scope','executive','--ids',','.join(ids),capture=True)
            if code or attempt['policies']['uncached_requests']:raise ValueError('Policy judgments remain pending')
            attempt['astra']=review_cohort(root,'archive_pilot',ids,allowance,2,set(ids),allow_x_context=False)
            if attempt['astra']['status']!='complete':raise ValueError('Astra review remains pending')
        audit['status']='pilot_complete'
    except Exception as exc:
        audit.update(status='pending',error=type(exc).__name__);raise
    finally:
        recover_additions()
        audit['spent_usd']=round(llm.spent('openrouter')-audit['budget_baseline'],6)
        audit['remaining_usd']=round(archive.remaining(audit['budget_baseline'],audit['limit_usd'],llm.spent('openrouter')),6)
        audit['new_statements']=sum(map(len,audit['added'].values()));federal.write(path,audit)
    federal_analysis.build(root,record=True);federal.build(root)
    return audit


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['discover','pilot']);args=p.parse_args()
    if args.command=='pilot':result=pilot(ROOT)
    else:
        config=federal.read(ROOT/'config/federal_archives.json',{});state=federal.read(ROOT/archive.STATE,{'version':1,'documents':{},'indexes':{}})
        subjects=[s for s in policy_subjects.load_subjects(ROOT) if s['id'] in PILOT_IDS]
        errors=archive.discover(ROOT,config,subjects,state);federal.write(ROOT/archive.STATE,state)
        result={'documents':len(state['documents']),'indexes':state['indexes'],'errors':errors,'paid_calls':0}
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
