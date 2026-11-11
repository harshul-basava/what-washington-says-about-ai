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
    if type(workers) is not int or not 1<=workers<=(8 if daily else 20):raise ValueError('workers must be 1–20 (1–8 for daily runs)')
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
    budget=Budget(max_cost,daily,metadata,wait_for_capacity=not daily and workers>8);errors=[];requests=0
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
                if daily:selected.sort(key=lambda s:int(s['sid'][1:]))
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
            except llm.BudgetExceeded:return job,{'response_received':attempt>0},'budget_exceeded'
            except llm.OpenRouterRequestError as exc:return job,None,f'openrouter_http_{exc.status_code}'
            except (ValueError,KeyError,TypeError):last_error='invalid_response'
            except Exception as exc:return job,None,type(exc).__name__
        return job,None,last_error
    scheduler_path=root/'data/federal_analysis_scheduler.json'
    scheduler_cursor=a.read(scheduler_path,{'version':1,'next_stage':None,'last_profile':{}}) if daily else {}
    def mark_turn(stage, turn):
        profile, batch, end = turn
        scheduler_cursor.setdefault('last_profile', {})[stage] = profile
        scheduler_cursor.setdefault('batch_cursor', {}).setdefault(stage, {})[profile] = [batch, end]
        a.write(scheduler_path, scheduler_cursor)

    def scheduled():
        if not daily:
            for stage in sequence:
                work=jobs(stage)
                if work:yield stage,work,None
            return
        # Rotate stages and profiles independently. A busy early profile or new
        # evidence must not reset the daily run to the same first-stage queue.
        cursor=scheduler_cursor
        start=sequence.index(cursor['next_stage']) if cursor.get('next_stage') in sequence else 0
        rotation=sequence[start:]+sequence[:start];attempted=set()
        while rotation:
            advanced=False
            for stage in rotation:
                candidates=[job for job in jobs(stage)
                    if (stage,job[0],tuple(s['sid'] for s in job[1])) not in attempted]
                if not candidates:
                    continue
                last_profile = cursor.get('last_profile', {}).get(stage, '')
                profile = min((job[0] for job in candidates), key=lambda pid: (pid <= last_profile, pid))
                batches = [(int(job[1][0]['sid'][1:]), job) for job in candidates if job[0] == profile]
                last_batch, end = cursor.get('batch_cursor', {}).get(stage, {}).get(profile, [0, 0])
                batch, job = min(batches, key=lambda row: (not last_batch < row[0] <= end, row[0]))
                if not last_batch < batch <= end:
                    # Bound each round so continuous arrivals cannot delay wraparound.
                    end = max(number for number, _ in batches)
                advanced = True
                attempted.add((stage, profile, tuple(s['sid'] for s in job[1])))
                cursor['next_stage']=sequence[(sequence.index(stage)+1)%len(sequence)]
                # Save before dispatch, including a blocked attempt, so one
                # temporarily unaffordable stage cannot monopolize every run.
                a.write(scheduler_path,cursor)
                # One job per turn prevents competing thread reservations.
                yield stage, [job], (profile, batch, end)
            if not advanced:return
    for stage, work, turn in scheduled():
        dispatched=False
        budget_blocked=False
        print(f'{stage}: {len(work)} requests planned',flush=True)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures=[pool.submit(assess,stage,job) for job in work]
            for future in as_completed(futures):
                job,result,error=future.result();pid,ss,areas=job;requests+=1
                if error!='budget_exceeded' or (result and result.get('response_received')):
                    dispatched=True
                if error:
                    if error=='budget_exceeded':budget_blocked=True
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
        if daily and dispatched:
            # A response, including an invalid one, gives this profile a turn.
            mark_turn(stage, turn)
        if budget_blocked:
            if not daily or dispatched:
                break
            if llm.spent('openrouter')>budget.baseline:
                # The job could not start with the remaining allowance.
                scheduler_cursor['next_stage']=stage
                a.write(scheduler_path,scheduler_cursor)
                break
            # This job cannot fit even a fresh allowance. The current run's
            # attempted set lets other batches for this profile take a turn.
            mark_turn(stage, turn)
    report={**a.plan(root,ids),'estimated_cost_usd':round(llm.spent('openrouter')-budget.baseline,6),
            'requests':requests,'uncertain_cost_requests':budget.uncertain,'errors':errors}
    if errors:report['status']='partial'
    a.write(root/'data/federal_analysis_status.json',{'date':a.today(),**report})
    a.build(root,record=True)
    return report
