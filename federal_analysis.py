"""Offline federal broad analysis, cache validity, and publication.

The congressional rubric and fixed formula stay shared; assessments and exports do not.
"""
import calendar
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import policy_subjects
from scripts.phase3_label import DIMS, score_member, recent_cutoff

ROOT = Path(__file__).resolve().parent
DIMENSIONS = [{'id': k, 'title': v} for k,v in zip(DIMS,
    ['AI overall', 'AGI-pilled', 'AI x-risk', 'China race', 'Regulation'])]
TOPICS = ['jobs/economy','China/competition','national security','kids/online safety','deepfakes/elections',
          'copyright','energy/data centers','regulation','AGI/transformative','x-risk/loss of control','misuse (bio/cyber)','other']
REG_TEXT = (ROOT/'config/reg_focus.md').read_text()
REGULATION_AREAS = [{'id': k,'title':title.strip(),'group':'frontier' if REG_TEXT.index(f'| `{k}` |')>REG_TEXT.index('### Catastrophic') else 'harms'}
    for k,title in re.findall(r'^\| `([a-z_]+)` \| ([^|]+?) \|',REG_TEXT,re.M)]
AREA_IDS = [a['id'] for a in REGULATION_AREAS]
LABEL_PATH = 'data/federal_analysis_labels.json'
PROFILE_PATH = 'data/federal_analysis_profiles.json'

def read(path, default=None):
    return json.loads(Path(path).read_text()) if Path(path).exists() else default

def write(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=1)+'\n');temp.replace(path)

def today():return datetime.now(timezone.utc).date().isoformat()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def configuration(root):
    root=Path(root)
    return {'settings':read(root/'config/federal_analysis.json'),
            'rubric':(root/'config/rubric.md').read_text(),
            'regulation_rubric':(root/'config/reg_focus.md').read_text(),
            'prompt':(root/'config/federal_analysis_prompt.md').read_text()}

def subject_context(subject):
    return {k:subject.get(k) for k in ('id','name','entity_type','organization_id')} | {
        'roles':[{k:r.get(k) for k in ('organization_id','title','start_date','end_date','status')} for r in subject.get('roles',[])]}

def fingerprint(subject, statements, stage, config, legacy=False):
    evidence=[{k:s.get(k) for k in ('sid','text','date','url','source_type','attribution','verified','attribution_span_sha256')} for s in statements]
    semantic=config
    if not legacy:
        settings=config.get('settings',{})
        keys=('models','label_runs','confidence_min','high_stakes') if stage=='labels' else ('models',)
        semantic={'settings':{k:settings[k] for k in keys if k in settings},'prompt':config.get('prompt'),
                  'rubric':config.get('rubric') if stage=='labels' else config.get('regulation_rubric')}
    return digest({'subject':subject_context(subject),'evidence':evidence,'stage':stage,'config':semantic})

def inputs(root):
    subjects=[s for s in policy_subjects.load_subjects(root) if s['branch']=='executive']
    evidence={s['id']:[e for e in policy_subjects.load_evidence(root,s) if e.get('verified') is True and e.get('text') and e.get('url')] for s in subjects}
    return subjects,evidence

def parse_json(text):
    if not isinstance(text,str):raise ValueError('Missing model response text')
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result:raise ValueError('Duplicate response key')
            result[k]=v
        return result
    text=text.strip()
    if text.startswith('```') and text.endswith('```'):
        text=re.sub(r'^```(?:json)?\s*','',text)[:-3].strip()
    result=json.loads(text,object_pairs_hook=unique)
    if not isinstance(result,dict):raise ValueError('Response must be an object')
    return result

def parse_labels(text,sids):
    result=parse_json(text).get('statements')
    if not isinstance(result,dict) or set(result)!=set(sids):raise ValueError('Incomplete statement coverage')
    for row in result.values():
        if not isinstance(row,dict):raise ValueError('Invalid statement assessment')
        labels,confidence,topics=(row.get(k) for k in ('labels','confidence','topics'))
        if (not isinstance(labels,dict) or not set(labels)<=set(DIMS) or
            any(type(v) is not int or not 0<=v<=4 for v in labels.values())):raise ValueError('Invalid dimension label')
        if (not isinstance(confidence,dict) or set(confidence)!=set(labels) or
            any(type(v) not in (int,float) or not 1<=v<=5 for v in confidence.values())):raise ValueError('Invalid confidence')
        if (not isinstance(topics,list) or not 1<=len(topics)<=3 or len(set(topics))!=len(topics) or
            any(t not in TOPICS for t in topics)):raise ValueError('Invalid topics')
    return result

def citations(value,sids,required=True):
    if not isinstance(value,list) or len(set(value))!=len(value) or any(type(s) is not str or s not in sids for s in value):
        raise ValueError('Invalid source citations')
    if required and not 1<=len(value)<=6:raise ValueError('Missing source citations')
    return value

def parse_regulation(text,sids,areas):
    rows=parse_json(text).get('stances')
    if not isinstance(rows,dict) or set(rows)!=set(areas):raise ValueError('Incomplete regulation coverage')
    for row in rows.values():
        if not isinstance(row,dict) or type(row.get('stance')) is not int or row['stance'] not in (-2,-1,0,1,2):raise ValueError('Invalid regulation stance')
        citations(row.get('sids'),sids,bool(row['stance']))
        if row['stance']==0 and row['sids']:raise ValueError('No-stance result cannot cite support')
        if not isinstance(row.get('why'),str) or not row['why'].strip():raise ValueError('Missing regulation reason')
    return rows

def parse_summary(text,sids):
    rows=parse_json(text).get('sentences')
    if not isinstance(rows,list) or not 1<=len(rows)<=4:raise ValueError('Invalid summary')
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get('text'),str) or not row['text'].strip():raise ValueError('Invalid summary sentence')
        citations(row.get('sids'),sids)
    return {'status':'complete','text':' '.join(r['text'].strip() for r in rows),'sids':list(dict.fromkeys(s for r in rows for s in r['sids'])),'sentences':rows}

def resolve_labels(entry,settings=None):
    settings=settings or {'confidence_min':3,'high_stakes':{'x_risk':3,'agi_pilled':3}}
    assessments=entry.get('assessments',{});runs=[assessments.get(f'ds_{i}',{}).get('value') for i in range(3)]
    pending={'status':'pending','a':{},'b':{},'topics':[],'confidence':{},'escalated':[]}
    if any(r is None for r in runs):return pending
    major,conf,esc={}, {}, []
    for dim in DIMS:
        values=[r['labels'].get(dim) for r in runs];top,n=Counter(values).most_common(1)[0]
        cs=[r['confidence'][dim] for r in runs if dim in r['labels']];c=sum(cs)/len(cs) if cs else None
        if top is not None:major[dim]=top;conf[dim]=round(c,2)
        previous=entry.get('reference_scores',{}).get(dim)
        if any(v is not None for v in values) and (n!=3 or c<settings['confidence_min'] or
            (top is not None and top>=settings['high_stakes'].get(dim,9)) or
            (top is not None and type(previous) in (int,float) and abs(top-previous)>=2)):esc.append(dim)
    a,b=dict(major),dict(major)
    sol=assessments.get('sol',{}).get('value')
    if esc and sol is None:return {**pending,'next':'sol','confidence':conf,'escalated':esc}
    apart=[k for k in esc if k in major and k in sol['labels'] and abs(major[k]-sol['labels'][k])>=2] if sol else []
    astra=assessments.get('astra',{}).get('value')
    if apart and astra is None:return {**pending,'next':'astra','confidence':conf,'escalated':esc}
    for k in esc:
        b.pop(k,None)
        if k in sol['labels']:b[k]=sol['labels'][k]
        if astra and k in astra['labels'] and k in a and k in b:
            av=astra['labels'][k]
            if abs(av-a[k])>abs(av-b[k]):a[k]=av
            else:b[k]=av
    counts=Counter(t for r in runs for t in r['topics']);topics=[t for t,n in counts.most_common(3) if n>=2] or [counts.most_common(1)[0][0]]
    result={'status':'complete','a':a,'b':b,'topics':topics,'confidence':conf,'escalated':esc}
    review_record=assessments.get('astra_stance_review',{})
    review=review_record.get('value',{})
    if review.get('reviewed_dimension')=='ai_overall':
        label=review.get('labels',{}).get('ai_overall');confidence=review.get('confidence',{}).get('ai_overall')
        accepted=type(label) is int and 0<=label<=4 and type(confidence) in (int,float) and 3<=confidence<=5
        if accepted:
            a['ai_overall']=b['ai_overall']=label;conf['ai_overall']=confidence
        result['stance_review']={**review,'accepted':accepted,'model':review_record.get('model'),
            'assessed_at':review_record.get('assessed_at'),'generation_id':review_record.get('generation_id')}
    return result

def resolve_regulation(entry):
    assessments=entry.get('assessments',{});a=assessments.get('reg_ds',{}).get('value');b=assessments.get('reg_sol',{}).get('value')
    if a is None or b is None:return {'status':'pending','areas':{}}
    sign=lambda x:(x>0)-(x<0)
    disputed=[k for k in AREA_IDS if sign(a[k]['stance'])!=sign(b[k]['stance'])]
    third=assessments.get('reg_astra',{}).get('value')
    if disputed and (third is None or not set(disputed)<=set(third)):
        return {'status':'pending','areas':{},'disputed':disputed}
    final={k:(a[k] if abs(a[k]['stance'])<=abs(b[k]['stance']) else b[k]) for k in AREA_IDS if k not in disputed}
    final.update({k:third[k] for k in disputed})
    return {'status':'complete','areas':final,'disputed':disputed}

def date_end(value):
    if not isinstance(value,str):return None
    try:
        if re.fullmatch(r'\d{4}',value):return date(int(value),12,31).isoformat()
        if re.fullmatch(r'\d{4}-\d{2}',value):
            y,m=map(int,value.split('-'));return date(y,m,calendar.monthrange(y,m)[1]).isoformat()
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):return date.fromisoformat(value).isoformat()
    except ValueError:pass
    return None

def at_cutoff(statements,cutoff):return [s for s in statements if date_end(s.get('date')) and date_end(s['date'])<=cutoff]

def score(statements,resolved,asof):
    pending=any(resolved.get(s['sid'],{}).get('status')!='complete' for s in statements)
    scores={k:None for k in DIMS};details={}
    if pending or len(statements)<3:
        reason='pending' if pending else 'insufficient_evidence'
        return scores,{k:{'score':None,'reason_a':reason,'reason_b':reason,'sids':[],'label_count':0} for k in DIMS}
    labels={j:{s['sid']:resolved[s['sid']][slot] for s in statements} for j,slot in [('sonnet','a'),('gpt','b')]}
    values=score_member(labels,{s['sid']:date_end(s.get('date')) for s in statements},len(statements),recent_cutoff(asof))
    for k,(value,a,b) in values.items():
        scores[k]=value;details[k]={'score':value,'reason_a':a[1],'reason_b':b[1],
            'sids':list(dict.fromkeys(a[2]+b[2])),'label_count':sum(k in resolved[s['sid']]['a'] or k in resolved[s['sid']]['b'] for s in statements)}
    return scores,details

def valid_entry(saved,subject,statements,stage,config):
    entry=saved.get('profiles',{}).get(subject['id'],{})
    if stage=='labels':entry=entry.get(statements[0]['sid'],{})
    # Accept initial-run hashes only when the entire original configuration still matches.
    hashes={fingerprint(subject,statements,stage,config),fingerprint(subject,statements,stage,config,legacy=True)}
    return entry if entry.get('input_hash') in hashes else {}

def state(root):
    return read(Path(root)/LABEL_PATH,{'version':1,'profiles':{}}),read(Path(root)/PROFILE_PATH,{'version':1,'profiles':{}})

def plan(root,ids=None):
    config=configuration(root);subjects,evidence=inputs(root);labels,profiles=state(root)
    report={'profiles':0,'statements':0,'labeled_statements':0,'pending_labels':0,'pending_regulation':0,'pending_summaries':0,'pending_stages':{}}
    stages=Counter()
    for s in subjects:
        if ids is not None and s['id'] not in ids:continue
        report['profiles']+=1;ss=evidence[s['id']];report['statements']+=len(ss)
        for e in ss:
            row=valid_entry(labels,s,[e],'labels',config);resolved=resolve_labels(row,config['settings'])
            if resolved['status']=='complete':report['labeled_statements']+=1
            else:
                report['pending_labels']+=1
                stages.update(k for k in ('ds_0','ds_1','ds_2') if k not in row.get('assessments',{}))
                if resolved.get('next'):stages[resolved['next']]+=1
        entry=valid_entry(profiles,s,ss,'profile',config)
        if ss and resolve_regulation(entry)['status']!='complete':report['pending_regulation']+=1
        if ss and not entry.get('assessments',{}).get('summary'):report['pending_summaries']+=1
    report['pending_stages']=dict(stages)
    report['status']='partial' if any(report[k] for k in ('pending_labels','pending_regulation','pending_summaries')) else 'ok'
    return report

def month_ends(start,asof):
    current=date.fromisoformat(start);stop=date.fromisoformat(asof);result=[]
    while current<=stop:
        result.append(current.isoformat());year=current.year+(current.month==12);month=current.month%12+1
        current=date(year,month,calendar.monthrange(year,month)[1])
    return result

def chart_topics(statements,resolved):
    """Only completed, dated assessments enter the rolling topic charts."""
    rows=[]
    for statement in statements:
        assessment=resolved.get(statement['sid'],{})
        end=date_end(statement.get('date'))
        if end and assessment.get('status')=='complete':
            precision={4:'year',7:'month',10:'day'}[len(statement['date'])]
            rows.append({'date':end,'precision':precision,'topics':assessment['topics']})
    return rows

def build(root,asof=None,record=False):
    root=Path(root);asof=asof or today();config=configuration(root);subjects,evidence=inputs(root);labels,profiles=state(root)
    revision=digest([config,[(subject_context(s),evidence[s['id']],labels.get('profiles',{}).get(s['id']),profiles.get('profiles',{}).get(s['id'])) for s in subjects],asof])
    output=root/'site/data/federal_analysis';output.mkdir(parents=True,exist_ok=True);ids={s['id'] for s in subjects}
    for path in output.glob('*.json'):
        if path.stem not in ids:path.unlink()
    previous=read(root/'data/federal_analysis_scores.json',{})
    changes=read(root/'data/federal_analysis_changes.json',[])
    members=[];chart_profiles={};snapshots={pid:row for pid,row in previous.items() if pid in ids}
    observation_path=root/f'data/federal_analysis_snapshots/{asof}.json'
    observations=read(observation_path,{})
    for subject in subjects:
        pid=subject['id'];ss=evidence[pid]
        entries={e['sid']:valid_entry(labels,subject,[e],'labels',config) for e in ss}
        resolved={sid:resolve_labels(entry,config['settings']) for sid,entry in entries.items()}
        entry=valid_entry(profiles,subject,ss,'profile',config)
        regulation=resolve_regulation(entry) if ss else {'status':'no_evidence','areas':{}}
        summary=entry.get('assessments',{}).get('summary',{}).get('value',{'status':'pending' if ss else 'no_evidence','text':'','sids':[]})
        scores,details=score(ss,resolved,asof);complete=sum(v['status']=='complete' for v in resolved.values())
        status='no_evidence' if not ss else 'complete' if complete==len(ss) and regulation['status']=='complete' and summary['status']=='complete' else 'partial'
        topics=Counter()
        for r in resolved.values():
            if r['status']=='complete':
                for t in r['topics']:topics[t]+=1/len(r['topics'])
        member={**policy_subjects.public_profile(subject),'n_statements':len(ss),'n_labeled':complete,'status':status,
            'scores':scores,'score_details':details,'summary':summary,'topics':{k:round(v,3) for k,v in topics.items()},'regulation':regulation}
        members.append(member)
        if complete==len(ss):
            snapshots[pid]={'date':asof,'scores':scores,'complete':True,'evidence_hash':digest(ss)}
        old=previous.get(pid)
        if record and old and old.get('complete') and complete==len(ss):
            for dim in DIMS:
                a,b=old['scores'].get(dim),scores.get(dim)
                if a==b or a is None or b is None:continue
                event={'id':pid,'date':asof,'dimension':dim,'old':a,'new':b,'kind':'big' if abs(a-b)>=1 or (a>=3)!=(b>=3) else 'small',
                       'cause':'evidence or assessment changed' if old.get('evidence_hash')!=digest(ss) else 'score window or assessment changed','sids':details[dim]['sids']}
                if event not in changes:changes.append(event)
        history=[]
        for cutoff in month_ends(config['settings']['history_start'],asof):
            historical=at_cutoff(ss,cutoff);hscore,_=score(historical,resolved,cutoff)
            history.append({'date':cutoff,'scores':hscore,'n_statements':len(historical),
                'status':'pending' if any(resolved[s['sid']]['status']!='complete' for s in historical) else 'complete' if historical else 'no_evidence','kind':'reconstructed'})
        for path in sorted((root/'data/federal_analysis_snapshots').glob('*.json')):
            snapshot=read(path,{})
            if pid in snapshot and path.stem<=asof:
                row=snapshot[pid]
                history.append({'date':path.stem,'scores':row['scores'],'n_statements':row['n_statements'],'status':row['status'],'kind':'observed'})
        if record and complete==len(ss) and pid not in observations:
            observation={'scores':scores,'n_statements':len(ss),'status':'complete' if ss else 'no_evidence'}
            observations[pid]=observation
            history.append({'date':asof,**observation,'kind':'observed'})
        statement_records=[]
        for e in ss:
            item=policy_subjects.public_evidence(e)
            assessments=entries[e['sid']].get('assessments',{})
            used_models={('deepseek' if stage.startswith('ds_') else stage):result['model']
                         for stage,result in assessments.items()}
            statement_records.append({k:item.get(k) for k in ('sid','date','url','text','source_type','attribution')} | {
                'analysis':{**resolved[e['sid']],'models':used_models,
                    'assessments':{stage:{**r['value'],**{k:r.get(k) for k in ('model','assessed_at','generation_id')}}
                                   for stage,r in assessments.items()}}})
        history=sorted(history,key=lambda h:(h['date'],h['kind']))
        profile_changes=[c for c in changes if c['id']==pid]
        chart_profiles[pid]={'history':history,'topics':chart_topics(ss,resolved),'changes':profile_changes}
        write(output/f'{pid}.json',{'schema_version':1,'id':pid,'revision':revision,'profile':member,'statements':statement_records,
            'history':history,'changes':profile_changes})
    coverage=plan(root)
    result={'schema_version':1,'built_on':asof,'revision':revision,'dimensions':DIMENSIONS,'regulation_areas':REGULATION_AREAS,'topics':TOPICS,
        'methodology':{'models':config['settings']['models'],'text':"Five scores use the congressional rubric and fixed formula. Three DeepSeek passes trigger independent Sol/Astra review. Regulation uses DeepSeek and Sol with Astra for direction disagreements. Histories reconstruct dated evidence for today's eligible roster; they do not track historical office membership. A silence zero means no discussion in this corpus, not rejection."},
        'coverage':coverage,'organizations':policy_subjects.load_registry(root)['organizations'],'members':members}
    write(root/'site/data/federal_analysis.json',result)
    write(root/'site/data/federal_charts.json',{'schema_version':1,'revision':revision,'profiles':chart_profiles})
    if record:
        write(root/'data/federal_analysis_scores.json',snapshots);write(root/'data/federal_analysis_changes.json',changes)
        # Each profile's first complete daily observation is immutable. Other profiles can finish later.
        if observations:write(observation_path,observations)
    return result
