/* Congress chart conventions applied to the current federal roster. No model calls. */
(function (global) {
  'use strict';
  const view = () => typeof module !== 'undefined' && module.exports ? require('./federal-analysis.js') : global.FederalAnalysis;
  const esc = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = n => Number.isInteger(n) ? String(n) : n.toFixed(1);
  const DAY = 86400000;
  const date = value => Date.parse(value+'T00:00:00Z');
  const iso = value => new Date(value).toISOString().slice(0,10);
  const validScore = n => typeof n==='number' && Number.isFinite(n) && n>=0 && n<=4;
  const value = (m,d) => view().scoreState(m,d).value;
  const color = n => n===null ? 'var(--nodata)' : `var(--r${Math.round(n)})`;
  const topicColor = i => `var(--topic-${i % 12})`;
  const profileLink = (m,content,extra='') => `<a href="?scope=${m.entity_type==='institution'?'institutions':'officials'}&amp;profile=${encodeURIComponent(m.id)}#fa-profiles" data-profile="${esc(m.id)}" data-chart-profile ${extra}>${content}</a>`;
  const PRESETS = [
    {id:'agi_low_risk',title:'Expect AGI, low risk',high:'agi_pilled',low:'x_risk'},
    {id:'risk_low_rules',title:'High risk, low regulation',high:'x_risk',low:'regulation'},
    {id:'china_risk',title:'High China competition, high risk',high:'china_race',also:'x_risk'},
    {id:'rules_low_risk',title:'High regulation, low risk',high:'regulation',low:'x_risk'},
    {id:'benefits_rules',title:'High AI overall, high regulation',high:'ai_overall',also:'regulation'}
  ];
  function validateCharts(payload,data) {
    const ids=data.members.map(m=>m.id).sort();
    if (payload?.schema_version!==1 || payload.revision!==data.revision || !payload.profiles ||
        JSON.stringify(Object.keys(payload.profiles).sort())!==JSON.stringify(ids) ||
        ids.some(id=>!['history','topics','changes'].every(k=>Array.isArray(payload.profiles[id][k])))) {
      throw new Error('History and topic charts are missing or stale. Reload to get a matching export.');
    }
    return payload;
  }
  function agencyDistribution(members,dimension,organizations) {
    const orgs=new Map(organizations.map(o=>[o.id,o])), groups=new Map();
    for (const member of members) {
      let id=member.organization_id || 'unlisted', seen=new Set();
      while (orgs.get(id)?.parent_id && !seen.has(id)) {seen.add(id);id=orgs.get(id).parent_id;}
      if (!groups.has(id)) groups.set(id,{id,name:orgs.get(id)?.name || member.organization_name || 'Organization not listed',total:0,bins:[0,0,0,0,0],missing:0,members:[]});
      const group=groups.get(id),n=value(member,dimension);
      group.total++;group.members.push(member);
      if (n===null) group.missing++; else group.bins[Math.round(n)]++;
    }
    return [...groups.values()].sort((a,b)=>b.total-a.total || a.name.localeCompare(b.name));
  }
  function policyDistribution(members,areas) {
    return areas.map(area=>{
      const counts={'-2':0,'-1':0,'0':0,'1':0,'2':0};let unknown=0;
      for (const m of members) {
        const stance=m.regulation?.areas?.[area.id]?.stance ?? 0;
        if (m.regulation?.status==='complete' && Object.hasOwn(counts,stance)) counts[stance]++;
        else unknown++;
      }
      return {...area,counts,unknown,total:members.length};
    });
  }
  function cohortHistory(members,profiles,dimension,kind) {
    const rows=new Map();
    for (const m of members) for (const h of profiles[m.id]?.history || []) {
      if (h.kind!==kind || !Number.isFinite(date(h.date))) continue;
      if (!rows.has(h.date)) rows.set(h.date,{date:h.date,high:0,scored:0,total:members.length,percent:0});
      const row=rows.get(h.date),n=h.scores?.[dimension];
      if (h.status==='complete' && validScore(n)) {row.scored++;if (n>=3) row.high++;}
    }
    return [...rows.values()].sort((a,b)=>a.date.localeCompare(b.date)).map(r=>({...r,percent:r.total ? r.high/r.total*100 : 0}));
  }
  function topicTimeline(members,profiles,topics,start,end) {
    const events=members.flatMap(m=>profiles[m.id]?.topics || []).filter(e=>Number.isFinite(date(e.date)) && e.topics.length)
      .sort((a,b)=>a.date.localeCompare(b.date));
    const counts=Object.fromEntries(topics.map(t=>[t,0])),rows=[];
    let lo=0,hi=0;
    const change=(e,sign)=>{ for (const t of e.topics) if (Object.hasOwn(counts,t)) counts[t]+=sign/e.topics.length; };
    for (let day=date(start);day<=date(end);day+=DAY) {
      while (hi<events.length && date(events[hi].date)<=day) change(events[hi++],1);
      while (lo<hi && date(events[lo].date)<=day-30*DAY) change(events[lo++],-1);
      const total=hi-lo;
      rows.push({date:iso(day),total,shares:Object.fromEntries(topics.map(t=>[t,total ? Math.max(0,counts[t])/total*100 : null]))});
    }
    return rows;
  }
  function comparisonPoints(members,x,y) {
    return members.map(m=>({...m,x:value(m,x),y:value(m,y)})).filter(m=>m.x!==null && m.y!==null);
  }
  function presetMembers(members,id) {
    const p=PRESETS.find(p=>p.id===id) || PRESETS[0];
    return members.filter(m=>{
      const high=value(m,p.high),other=value(m,p.low || p.also);
      return high!==null && other!==null && high>=3 && (p.low ? other<2 : other>=3);
    });
  }
  function scoreLegend() {
    return `<div class="fc-legend">${[0,1,2,3,4].map(n=>`<span><i style="background:${color(n)}"></i>Score ${n}</span>`).join('')}<span><i style="background:var(--nodata)"></i>Unscored</span></div>`;
  }
  function renderDots(members,dimension) {
    if (!members.length) return '<p class="fa-empty">No profiles match these filters.</p>';
    const bins=[0,0,0,0,0,0], sorted=[...members].sort((a,b)=>(value(a,dimension)??5)-(value(b,dimension)??5)||a.name.localeCompare(b.name));
    for (const m of members) bins[value(m,dimension)===null ? 5 : Math.round(value(m,dimension))]++;
    let previous=0;
    const gradient=bins.map((n,i)=>{const start=previous;previous+=members.length ? n/members.length*100 : 0;return `${i===5?'var(--nodata)':color(i)} ${start}% ${previous}%`;}).join(',');
    return `<div class="fc-dot-layout"><div class="fc-dots">${sorted.map(m=>{
      const label=m.name+': '+view().scoreState(m,dimension).label;
      return profileLink(m,'',`class="fc-dot" style="--dot:${color(value(m,dimension))}" title="${esc(label)}" aria-label="${esc(label)}"`);
    }).join('')}</div><div class="fc-pie-wrap"><div class="fc-pie" role="img" aria-label="${esc(bins.map((n,i)=>`${i===5?'Unscored':'Score '+i}: ${n}`).join('. '))}" style="background:conic-gradient(${members.length?gradient:'var(--nodata) 0% 100%'})"></div><p>${members.length ? fmt(members.filter(m=>value(m,dimension)!==null && value(m,dimension)>=3).length/members.length*100) : 0}% score 3 or more</p></div></div>${scoreLegend()}`;
  }
  function renderAgencies(members,dimension,organizations) {
    return `<div class="fc-agencies">${agencyDistribution(members,dimension,organizations).map(g=>`<div class="fc-agency"><span>${esc(g.name)} <small>(${g.total})</small></span><div class="fc-stack">${[...g.bins,g.missing].map((n,i)=>n ? `<button type="button" data-agency-group="${esc(g.id)}" style="width:${n/g.total*100}%;background:${i===5?'var(--nodata)':color(i)}" aria-label="${esc(g.name)}: ${n} ${i===5?'unscored':'at score '+i}. Show profiles." title="${n} of ${g.total} · ${fmt(n/g.total*100)}%">${n/g.total>=.09?n:''}</button>` : '').join('')}</div></div>`).join('')}</div>${scoreLegend()}`;
  }
  function lineChart(series,{title,yMax=100,percent=true,connect=true}={}) {
    const all=series.flatMap(s=>s.rows),dates=all.map(r=>date(r.date));
    if (!dates.length) return '<p class="fa-empty">No dated records in this view.</p>';
    const min=Math.min(...dates),max=Math.max(...dates),w=800,h=240,l=42,r=16,t=18,b=30;
    const x=d=>min===max ? (w+l-r)/2 : l+(date(d)-min)/(max-min)*(w-l-r), y=n=>t+(1-n/yMax)*(h-t-b);
    const ticks=[0,.25,.5,.75,1].map(f=>f*yMax);
    return `<svg class="fc-line-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(title)}">
      ${ticks.map(n=>`<line class="fa-grid" x1="${l}" y1="${y(n)}" x2="${w-r}" y2="${y(n)}"/><text x="${l-8}" y="${y(n)+4}" text-anchor="end">${n}${percent?'%':''}</text>`).join('')}
      ${series.map(s=>{
        const paths=[];let path=[];
        for (const row of s.rows) {if (row.value===null) {if(path.length)paths.push(path);path=[];} else path.push([x(row.date),y(row.value)]);}
        if(path.length)paths.push(path);
        return `<g style="color:${s.color}">${connect?paths.map(p=>`<polyline points="${p.map(x=>x.map(n=>n.toFixed(2)).join(',')).join(' ')}"/>`).join(''):''}${s.rows.length<=100?s.rows.filter(r=>r.value!==null).map(row=>`<circle cx="${x(row.date)}" cy="${y(row.value)}" r="3"><title>${esc(s.name)} · ${esc(row.date)}: ${fmt(row.value)}${percent?'%':''}</title></circle>`).join(''):''}</g>`;
      }).join('')}<text x="${l}" y="${h-5}">${iso(min)}</text>${min!==max?`<text x="${w-r}" y="${h-5}" text-anchor="end">${iso(max)}</text>`:''}</svg>`;
  }
  function renderTimeline(members,profiles,dimension,kind) {
    const rows=cohortHistory(members,profiles,dimension,kind);
    return lineChart([{name:'Current cohort',rows:rows.map(r=>({...r,value:r.percent})),color:'var(--accent)'}],{title:'Percentage of the selected profiles with scores of 3 or more',connect:kind==='reconstructed'})+
      `<details><summary>Exact dates and counts (${rows.length})</summary><div class="fa-table-scroll fc-data-table"><table><thead><tr><th>Date</th><th>Score ≥3</th><th>Scored</th><th>All profiles</th><th>Share ≥3</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${r.date}</td><td>${r.high}</td><td>${r.scored}</td><td>${r.total}</td><td>${fmt(r.percent)}%</td></tr>`).join('')}</tbody></table></div></details>`;
  }
  function renderPolicies(members,areas,selected) {
    const rows=policyDistribution(members,areas), max=Math.max(1,...rows.flatMap(r=>[r.counts[-2]+r.counts[-1],r.counts[1]+r.counts[2]]));
    let group=null;
    return `<div class="fc-legend"><span><i class="fc-opposed"></i>Explicit opposition</span><span><i class="fc-opposed fc-implied"></i>Implied opposition</span><span><i class="fc-supported fc-implied"></i>Implied support</span><span><i class="fc-supported"></i>Explicit support</span></div><div class="fc-policies">${rows.map(row=>{
      const heading=row.group!==group?`<h3>${row.group==='harms'?'Present-day harms':'Frontier and catastrophic risk'}</h3>`:'';group=row.group;
      const negative=row.counts[-2]+row.counts[-1],positive=row.counts[1]+row.counts[2];
      return `${heading}<button type="button" class="fc-policy-row" data-rule="${esc(row.id)}" aria-pressed="${selected===row.id}" aria-label="${esc(row.title)}: ${negative} oppose, ${positive} support, ${row.counts[0]} no stated position, ${row.unknown} unassessed. Show profiles."><span>${esc(row.title)}</span><span class="fc-diverging"><span class="fc-negative">${[-2,-1].map(n=>`<i class="fc-opposed ${n===-1?'fc-implied':''}" style="width:${row.counts[n]/max*100}%"></i>`).join('')}</span><span class="fc-positive">${[1,2].map(n=>`<i class="fc-supported ${n===1?'fc-implied':''}" style="width:${row.counts[n]/max*100}%"></i>`).join('')}</span></span><small>${negative} / ${positive}</small></button>`;
    }).join('')}</div><p class="fa-note">Counts: oppose / support. Each side uses the same scale, from 0 to ${max} profiles. This view includes ${members.length} profiles. No stated position does not mean opposition.</p>`;
  }
  function renderPolicySelection(members,areas,id) {
    const area=areas.find(a=>a.id===id);if(!area)return '';
    return `<div class="fc-selection"><h3>${esc(area.title)}</h3>${[2,1,-1,-2].map(stance=>{
      const rows=members.filter(m=>m.regulation?.status==='complete' && m.regulation.areas?.[id]?.stance===stance);
      return `<p><strong>${{'2':'Explicit support','1':'Implied support','-1':'Implied opposition','-2':'Explicit opposition'}[stance]} (${rows.length})</strong></p><div class="fc-profile-chips">${rows.length?rows.map(m=>profileLink(m,esc(m.name))).join(''):'<span class="fa-muted">No profiles</span>'}</div>`;
    }).join('')}</div>`;
  }
  function renderScatter(members,xDim,yDim,dimensions) {
    const rows=comparisonPoints(members,xDim,yDim),w=800,h=320,l=48,t=16,r=20,b=40;
    const x=n=>l+n/4*(w-l-r),y=n=>t+(4-n)/4*(h-t-b);
    // Small deterministic visual offsets expose ties; tooltips always retain exact scores.
    const tied=new Map();
    return `<svg class="fc-scatter" viewBox="0 0 ${w} ${h}" role="group" aria-label="Compare two AI scores; each point opens a profile">${[0,1,2,3,4].map(n=>`<line class="fa-grid" x1="${l}" y1="${y(n)}" x2="${w-r}" y2="${y(n)}"/><text x="${l-10}" y="${y(n)+4}" text-anchor="end">${n}</text><text x="${x(n)}" y="${h-20}" text-anchor="middle">${n}</text>`).join('')}${rows.map(m=>{
      const key=m.x+':'+m.y,index=tied.get(key)||0;tied.set(key,index+1);
      const radius=index?3*Math.sqrt(index):0,angle=index*2.4;
      const tip=`${m.name}: ${dimensions.find(d=>d.id===xDim)?.title} ${fmt(m.x)}; ${dimensions.find(d=>d.id===yDim)?.title} ${fmt(m.y)}`;
      return profileLink(m,`<circle cx="${x(m.x)+Math.cos(angle)*radius}" cy="${y(m.y)+Math.sin(angle)*radius}" r="6" style="fill:${color(m.y)}"><title>${esc(tip)}</title></circle>`,`aria-label="${esc(tip)}"`);
    }).join('')}</svg><p class="fa-note">${rows.length} profiles have both scores. Small offsets separate equal scores. Point details show exact values.</p>`;
  }
  function renderTopicShare(members,profiles,topics,range,end) {
    const dates=members.flatMap(m=>(profiles[m.id]?.topics||[]).map(r=>r.date)).filter(d=>d<=end).sort();
    if(!dates.length) return '<p class="fa-empty">No dated, assessed statements in this view.</p>';
    const start=range==='all'?dates[0]:iso(date(end)-(range==='3m'?90:365)*DAY);
    const rows=topicTimeline(members,profiles,topics,start,end),w=800,h=250,l=42,r=16,t=10,b=30;
    const x=i=>l+i/Math.max(1,rows.length-1)*(w-l-r),y=n=>t+(100-n)/100*(h-t-b);
    const cumulative=rows.map(row=>{let n=0;return topics.map(topic=>{const bottom=n;n+=row.shares[topic]||0;return {bottom,top:n};});});
    const segments=[];let run=[];
    rows.forEach((row,i)=>{if(!row.total){if(run.length)segments.push(run);run=[];}else run.push(i);});if(run.length)segments.push(run);
    const paths=topics.map((topic,k)=>`<g fill="${topicColor(k)}">${segments.map(segment=>`<path d="M${segment.map(i=>`${x(i).toFixed(1)},${y(cumulative[i][k].top).toFixed(1)}`).join('L')}L${[...segment].reverse().map(i=>`${x(i).toFixed(1)},${y(cumulative[i][k].bottom).toFixed(1)}`).join('L')}Z"><title>${esc(topic)}</title></path>`).join('')}</g>`).join('');
    return `<svg class="fc-topic-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Topic shares of statements in a rolling 30-day window. Exact values appear below.">${paths}${[0,25,50,75,100].map(n=>`<text x="${l-8}" y="${y(n)+4}" text-anchor="end">${n}%</text>`).join('')}<text x="${l}" y="${h-5}">${start}</text><text x="${w-r}" y="${h-5}" text-anchor="end">${end}</text></svg><div class="fc-legend">${topics.map((topic,i)=>`<span><i style="background:${topicColor(i)}"></i>${esc(topic)}</span>`).join('')}</div><details><summary>Exact daily shares (${rows.length} dates)</summary><div class="fa-table-scroll fc-data-table"><table><thead><tr><th>Date</th><th>Statements</th>${topics.map(t=>`<th>${esc(t)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr><td>${row.date}</td><td>${row.total}</td>${topics.map(t=>`<td>${row.shares[t]===null?'—':fmt(row.shares[t])+'%'}</td>`).join('')}</tr>`).join('')}</tbody></table></div></details>`;
  }
  function renderVoices(members,topic) {
    const rows=members.filter(m=>(m.topics?.[topic]||0)>0).sort((a,b)=>b.topics[topic]-a.topics[topic]||a.name.localeCompare(b.name)).slice(0,15),max=rows[0]?.topics[topic]||1;
    return rows.length ? `<div class="fc-voices">${rows.map(m=>profileLink(m,`<span>${esc(m.name)}</span><span class="fc-voice-track"><i style="width:${m.topics[topic]/max*100}%"></i></span><strong>${fmt(m.topics[topic])}</strong>`,`class="fc-voice"`)).join('')}</div>` : '<p class="fa-empty">No assessed statements address this topic in the selected profiles.</p>';
  }
  function renderMembers(members,dimensions) {
    return `<div class="fa-table-scroll fc-member-table"><table><caption class="fa-sr-only">All selected profiles and their five scores</caption><thead><tr><th>Profile</th>${dimensions.map(d=>`<th>${esc(d.title)}</th>`).join('')}<th>Quotes</th></tr></thead><tbody>${members.map(m=>`<tr><th>${profileLink(m,esc(m.name))}<small>${esc(m.organization_name||'')}</small></th>${dimensions.map(d=>{const state=view().scoreState(m,d.id);return `<td><span class="fc-score-chip ${state.value===null?'fc-missing':''}" style="--score:${color(state.value)}" title="${esc(state.label)}">${state.value===null?'—':fmt(state.value)}</span></td>`;}).join('')}<td>${m.n_statements}</td></tr>`).join('')}</tbody></table></div>`;
  }
  function renderRecent(members,profiles,dimension,end) {
    const rows=members.flatMap(m=>(profiles[m.id]?.changes||[]).filter(c=>c.dimension===dimension && c.date<=end && date(c.date)>=date(end)-60*DAY).map(c=>({...c,member:m}))).sort((a,b)=>b.date.localeCompare(a.date));
    return rows.length?`<div class="fa-table-scroll"><table><thead><tr><th>Date</th><th>Profile</th><th>Score change</th><th>Cause</th></tr></thead><tbody>${rows.slice(0,30).map(c=>`<tr><td>${esc(c.date)}</td><td>${profileLink(c.member,esc(c.member.name))}</td><td>${fmt(c.old)} → ${fmt(c.new)}</td><td>${esc(c.cause)}</td></tr>`).join('')}</tbody></table></div>`:'<p class="fa-empty">No observed score changes in the past 60 days. Daily snapshots will populate this view.</p>';
  }
  const api={validateCharts,agencyDistribution,policyDistribution,cohortHistory,topicTimeline,comparisonPoints,presetMembers,
    scoreLegend,renderDots,renderAgencies,renderTimeline,renderPolicies,renderPolicySelection,renderScatter,renderTopicShare,renderVoices,renderMembers,renderRecent,PRESETS};
  if(typeof module!=='undefined' && module.exports) module.exports=api;else global.FederalCharts=api;
})(typeof window!=='undefined'?window:globalThis);
