"""Paid, bounded and resumable federal analysis. Offline exports live in federal_analysis."""
import json
import math
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path

import federal_analysis as a

from model_budget import Budget


def messages(subject,statements,stage,config,areas=None):
    base=config['prompt']+'\n\nSubject and role context:\n'+json.dumps(a.subject_context(subject),ensure_ascii=False)
    if stage.startswith('ds_') or stage in ('sol','astra'):
        base+='\n\nFive-score rubric:\n'+config['rubric']
        output={'statements':{s['sid']:{'labels':{},'confidence':{},'topics':['other']} for s in statements}}
        task='Assess every supplied statement. Use labels {dimension: integer 0–4}, confidence {the same dimension: number 1–5}, and 1–3 topics. Empty labels means no dimension applies. Return every statement ID. Valid topics: '+json.dumps(a.TOPICS)
    elif stage.startswith('reg_'):
        base+='\n\nRegulation rubric:\n'+config['regulation_rubric']
        output={'stances':{k:{'stance':0,'sids':[],'why':'No stance in the supplied evidence.'} for k in (areas or a.AREA_IDS)}}
        task='Assess exactly these categories: '+', '.join(areas or a.AREA_IDS)+'. Use 0 for no stance; otherwise use -2, -1, 1, or 2 with source IDs and a reason. Read all supplied statements.'
    else:
        output={'sentences':[{'text':'One short evidence-based sentence.','sids':[statements[0]['sid']]}]}
        task='Write a concise neutral summary, with 1–4 individually cited sentences. Use only the supplied evidence.'
    # All judges receive original evidence, never a preceding model's answer.
    evidence=[{k:s.get(k) for k in ('sid','date','source_type','url','text','attribution')} for s in statements]
    return [{'role':'system','content':base}, {'role':'user','content':task+'\n\nEvidence:\n'+json.dumps(evidence,ensure_ascii=False)+
        '\n\nReturn only JSON with this structure (replace example values with the assessment):\n'+json.dumps(output)}]


def run(root,max_cost=5,workers=4,ids=None,daily=False,dry=False,stages=None):
    root=Path(root)
    if dry:return a.plan(root,ids)
    if type(workers) is not int or not 1<=workers<=8:raise ValueError('workers must be 1–8')
    import llm
    config=a.configuration(root);settings=config['settings'];subjects,evidence=a.inputs(root)
    if ids is not None:
        known={s['id'] for s in subjects}
        if not set(ids)<=known:raise ValueError('Unknown or excluded federal profile')
        subjects=[s for s in subjects if s['id'] in ids]
    labels,profiles=a.state(root);previous=a.read(root/'data/federal_analysis_scores.json',{})
    migrated_labels=migrated_profiles=False
    for subject in subjects:
        pid=subject['id'];ss=evidence[pid]
        for s in ss:
            existing=a.valid_entry(labels,subject,[s],'labels',config)
            if not existing:
                labels.setdefault('profiles',{}).setdefault(pid,{})[s['sid']]={'input_hash':a.fingerprint(subject,[s],'labels',config),
                    'reference_scores':previous.get(pid,{}).get('scores',{}),'assessments':{}}
            elif existing['input_hash']!=a.fingerprint(subject,[s],'labels',config):
                existing['input_hash']=a.fingerprint(subject,[s],'labels',config);migrated_labels=True
        if not a.valid_entry(profiles,subject,ss,'profile',config):
            profiles.setdefault('profiles',{})[pid]={'input_hash':a.fingerprint(subject,ss,'profile',config),'assessments':{}}
        elif profiles['profiles'][pid]['input_hash']!=a.fingerprint(subject,ss,'profile',config):
            profiles['profiles'][pid]['input_hash']=a.fingerprint(subject,ss,'profile',config);migrated_profiles=True
    if migrated_labels:a.write(root/a.LABEL_PATH,labels)
    if migrated_profiles:a.write(root/a.PROFILE_PATH,profiles)
    # An already complete run needs no credentials or network.
    before=a.plan(root,ids)
    if before['status']=='ok':
        a.build(root,record=True)
        return {**before,'estimated_cost_usd':0,'requests':0,'errors':[]}
    if not math.isfinite(max_cost) or max_cost < 0:
        raise ValueError('max_cost must be finite and nonnegative')
    if max_cost == 0:
        report={**before,'estimated_cost_usd':0,'requests':0,'errors':[{'error':'budget_exceeded'}]}
        a.write(root/'data/federal_analysis_status.json',{'date':a.today(),**report})
        a.build(root,record=True)
        return report
    if not llm.os.environ.get('OPENROUTER_API_KEY'):raise ValueError('OPENROUTER_API_KEY is required for incomplete analysis')
    result=llm.httpx.get('https://openrouter.ai/api/v1/models',timeout=30);result.raise_for_status()
    metadata={m['id']:m for m in result.json()['data'] if m['id'] in settings['models'].values()}
    if set(metadata)!=set(settings['models'].values()):raise ValueError('Configured analysis model is unavailable')
    budget=Budget(max_cost,daily,metadata);errors=[];requests=0
    sequence=['ds_0','ds_1','ds_2','sol','astra','reg_ds','reg_sol','reg_astra','summary']
    if stages is not None:
        if not set(stages)<=set(sequence):raise ValueError('Unknown analysis stage')
        sequence=[s for s in sequence if s in stages]
    byid={s['id']:s for s in subjects}
    def jobs(stage):
        work=[]
        for subject in subjects:
            pid=subject['id'];ss=evidence[pid]
            if not ss:continue
            if stage.startswith('ds_') or stage in ('sol','astra'):
                selected=[]
                for s in ss:
                    entry=labels['profiles'][pid][s['sid']]
                    if stage.startswith('ds_'):
                        if stage not in entry['assessments']:selected.append(s)
                    elif a.resolve_labels(entry,settings).get('next')==stage:selected.append(s)
                for offset in range(0,len(selected),settings['labels_batch_size']):work.append((pid,selected[offset:offset+settings['labels_batch_size']],None))
            else:
                entry=profiles['profiles'][pid]
                if stage in entry['assessments']:continue
                areas=None
                if stage=='reg_astra':
                    resolved=a.resolve_regulation(entry)
                    if resolved['status']!='pending' or not resolved.get('disputed'):continue
                    areas=resolved['disputed']
                work.append((pid,ss,areas))
        return work
    def assess(stage,job):
        pid,ss,areas=job
        role='deepseek' if stage.startswith('ds_') or stage in ('reg_ds','summary') else 'sol' if stage in ('sol','reg_sol') else 'astra'
        model=settings['models'][role];prompt=messages(byid[pid],ss,stage,config,areas)
        supported=metadata[model].get('supported_parameters',[]);options={}
        if 'reasoning' in supported:options['reasoning']={'effort':'medium' if role=='astra' else 'low'}
        if 'temperature' in supported:options['temperature']=0.7 if stage.startswith('ds_') else 0
        max_tokens=6000 if stage=='summary' else settings['max_output_tokens']
        last_error=None
        for attempt in range(2):
            try:
                # A valid provider response can exhaust its reasoning allowance before emitting JSON.
                # Retry with a separately reserved larger output allowance; never treat it as silence.
                result=budget.call(model,prompt,max_tokens*(attempt+1),('daily_' if daily else '')+'federal_analysis_'+stage,**options)
                content=result['choices'][0]['message']['content'];sids={s['sid'] for s in ss}
                if stage.startswith('ds_') or stage in ('sol','astra'):value=a.parse_labels(content,sids)
                elif stage.startswith('reg_'):value=a.parse_regulation(content,sids,areas or a.AREA_IDS)
                else:value=a.parse_summary(content,sids)
                return job,{'value':value,'model':model,'generation_id':result.get('id'),'assessed_at':datetime.now(timezone.utc).isoformat()},None
            except llm.BudgetExceeded:return job,None,'budget_exceeded'
            except llm.OpenRouterRequestError as exc:return job,None,f'openrouter_http_{exc.status_code}'
            except (ValueError,KeyError,TypeError):last_error='invalid_response'
            except Exception as exc:return job,None,type(exc).__name__
        return job,None,last_error
    for stage in sequence:
        work=jobs(stage)
        if not work:continue
        print(f'{stage}: {len(work)} requests planned',flush=True)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures=[pool.submit(assess,stage,job) for job in work]
            for future in as_completed(futures):
                job,result,error=future.result();pid,ss,areas=job;requests+=1
                if error:
                    errors.append({'stage':stage,'profile':pid,'error':error})
                    print(f'{stage} {pid}: {error}; saved work remains resumable',flush=True)
                    continue
                if stage.startswith('ds_') or stage in ('sol','astra'):
                    for s in ss:
                        labels['profiles'][pid][s['sid']]['assessments'][stage]={**result,'value':result['value'][s['sid']]}
                    a.write(root/a.LABEL_PATH,labels)
                else:
                    profiles['profiles'][pid]['assessments'][stage]=result;a.write(root/a.PROFILE_PATH,profiles)
                print(f'{stage} {pid}: saved; cost ${llm.spent("openrouter")-budget.baseline:.3f}',flush=True)
        if any(e['error']=='budget_exceeded' for e in errors):break
    report={**a.plan(root,ids),'estimated_cost_usd':round(llm.spent('openrouter')-budget.baseline,6),
            'requests':requests,'uncertain_cost_requests':budget.uncertain,'errors':errors}
    if errors:report['status']='partial'
    a.write(root/'data/federal_analysis_status.json',{'date':a.today(),**report})
    a.build(root,record=True)
    return report
