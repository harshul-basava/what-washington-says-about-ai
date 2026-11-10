/* Offline policy charts. All calculations use published judgments, not new model calls. */
(function (global) {
  'use strict';
  const RAW = ['support','oppose','mixed','neutral','unclear','disputed'];
  // mixed, description-only and unclear read as one group on the charts
  const STANCES = ['support','oppose','other','disputed'];
  const GROUP = s => ['mixed','neutral','unclear'].includes(s) ? 'other' : s;
  const LABELS = {support:'Support',oppose:'Oppose',other:'Mixed or unclear',disputed:'Models disagree'};
  const PARTIES = {D:'Democrats',R:'Republicans',I:'Independents'};
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const blank = () => Object.fromEntries(STANCES.map(s=>[s,0]));
  const percent = (n,d) => d > 0 ? Math.max(0,Math.min(100,100*n/d)) : 0;
  const party = p => /^dem|^dfl$|^D$/i.test(p) ? 'D' : /^rep|^R$/i.test(p) ? 'R' : 'I';
  const relevant = r => RAW.includes(r.stance);
  const countText = counts => STANCES.filter(s=>counts[s]).map(s=>`${counts[s]} ${LABELS[s].toLowerCase()}`).join(', ');

  function breakdown(members, target) {
    const result = {total:members.length, observed:0, missing:0, pending:0, counts:blank()};
    for (const member of members) {
      const row = member.policies[target];
      if (!row || ['pending','partial'].includes(row.coverage)) result.pending++;
      else if (row.relevant > 0 && RAW.includes(row.stance)) {
        result.counts[GROUP(row.stance)]++;
        result.observed++;
      } else result.missing++;
    }
    return result;
  }

  function monthIndex(value) {
    const match = /^(\d{4})-(\d{2})(?:-(\d{2}))?$/.exec(value || '');
    if (!match) return null;
    const year = +match[1], month = +match[2], day = +(match[3] || 1);
    if (year < 100 || month < 1 || month > 12 || day < 1 || day > new Date(Date.UTC(year,month,0)).getUTCDate()) return null;
    return year*12+month-1;
  }

  function timeline(records) {
    const rows = records.filter(relevant);
    const dated = rows.map(row=>({row, month:monthIndex(row.date)})).filter(r=>r.month !== null);
    const result = {periods:[], granularity:'month', excludedDates:rows.length-dated.length,
      pending:records.filter(r=>['pending','review_required'].includes(r.stance)).length};
    if (!dated.length) return result;
    const min = Math.min(...dated.map(r=>r.month)), max = Math.max(...dated.map(r=>r.month));
    const size = max-min > 17 ? 3 : 1;
    result.granularity = size === 3 ? 'quarter' : 'month';
    const first = Math.floor(min/size), last = Math.floor(max/size);
    for (let bucket=first; bucket<=last; bucket++) {
      const month=bucket*size, year=Math.floor(month/12), within=month%12;
      const key=size===3 ? `${year}-Q${within/3+1}` : `${year}-${String(within+1).padStart(2,'0')}`;
      const label=size===3 ? `Q${within/3+1} ’${String(year).slice(-2)}` : `${['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][within]} ’${String(year).slice(-2)}`;
      result.periods.push({key,label,total:0,people:0,counts:blank(),ids:new Set()});
    }
    for (const {row,month} of dated) {
      const period=result.periods[Math.floor(month/size)-first];
      period.counts[GROUP(row.stance)]++;
      period.total++;
      period.ids.add(row.person_id);
    }
    result.periods.forEach(p=>{p.people=p.ids.size; delete p.ids;});
    return result;
  }

  function facetCounts(records, facets) {
    const rows=records.filter(relevant);
    return facets.map(id=>({id,agreed:rows.filter(r=>r.facets_final ? r.final_judge === 'deepseek' && r.facets_final.includes(id) : r.facets_agreed.includes(id)).length,
      disputed:rows.filter(r=>r.facets_final ? r.final_judge === 'astra' && r.facets_final.includes(id) : r.facets_disputed.includes(id)).length}));
  }

  function stanceBar(row) {   // every profile in the view: stances, then "no evidence" (no relevant statements, or not assessed yet)
    const total = row.total ?? row.observed, none = Math.max(0, total - row.observed);
    if (!total) return '<div class="pc-empty-bar">No profiles in this view</div>';
    const seg = (cls, label, n) => `<span class="pc-fill pc-${cls}" style="width:${percent(n,total)}%" title="${esc(label)}: ${n} of ${total} profiles (${percent(n,total).toFixed(1)}%)" aria-hidden="true">${percent(n,total)>=6 ? n : ''}</span>`;
    return `<div class="pc-stack" role="img" aria-label="${esc(countText(row.counts))}${none ? `, ${none} no evidence` : ''}; ${total} profiles total">${
      STANCES.filter(s=>row.counts[s]).map(s=>seg(s, LABELS[s], row.counts[s])).join('')}${none ? seg('none','No evidence',none) : ''}</div>`;
  }

  function legend() {
    return `<div class="pc-legend" aria-label="Stance colors">${STANCES.map(s=>`<span><i class="pc-${s}" aria-hidden="true"></i>${LABELS[s]}</span>`).join('')}<span><i class="pc-none" aria-hidden="true"></i>No evidence</span></div>`;
  }

  function coverage(row) {
    return `<span class="pc-coverage"><span>${row.observed} / ${row.total}</span><span class="pc-track" aria-hidden="true"><span style="width:${percent(row.observed,row.total)}%"></span></span>${row.pending ? `<small>${row.pending} incomplete</small>` : ''}</span>`;
  }

  function exactTable(rows, title) {
    return `<details class="pc-exact"><summary>${esc(title)}</summary><div class="pc-table-wrap"><table><thead><tr><th scope="col">Group</th>${STANCES.map(s=>`<th scope="col">${LABELS[s]}</th>`).join('')}<th scope="col">No evidence</th><th scope="col">Incomplete</th></tr></thead><tbody>${rows.map(row=>`<tr><th scope="row">${esc(row.title)}</th>${STANCES.map(s=>`<td>${row.counts[s]}</td>`).join('')}<td>${row.missing}</td><td>${row.pending}</td></tr>`).join('')}</tbody></table></div></details>`;
  }

  function renderOverview(root, members, policies, selected, onSelect) {
    const rows=policies.map(p=>({...breakdown(members,p.id),id:p.id,title:p.title}));
    root.innerHTML = `<h3>Policy positions at a glance</h3>
      ${legend()}<div class="pc-overview-head" aria-hidden="true"><span>Policy or question</span><span>Positions of all profiles in this view</span></div>
      ${rows.map(row=>`<div class="pc-overview-row"><button type="button" class="pc-policy-link" data-policy="${esc(row.id)}" aria-current="${row.id===selected ? 'true' : 'false'}">${esc(row.title)}</button>${stanceBar(row)}</div>`).join('')}
      ${exactTable(rows,'Exact counts for every policy')}`;
    root.querySelectorAll('[data-policy]').forEach(button=>button.addEventListener('click',()=>onSelect(button.dataset.policy)));
  }

  function timelineHTML(result, width) {
    const {periods}=result;
    if (!periods.length) return '<p class="pc-empty">No relevant statements have a usable month or day in this selection.</p>';
    const rawMax=Math.max(...periods.map(p=>p.total));
    const step=Math.max(1,Math.pow(10,Math.floor(Math.log10(rawMax)))/2);
    const max=Math.ceil(rawMax/step)*step;
    const tickCount=Math.max(2,Math.floor((width-45)/85));
    const every=Math.max(1,Math.ceil((periods.length-1)/(tickCount-1)));
    const tickIndexes=periods.map((_,i)=>i).filter(i=>i%every===0 && i<periods.length-1);
    if (tickIndexes.length && periods.length-1-tickIndexes.at(-1)<every*.65) tickIndexes.pop();
    tickIndexes.push(periods.length-1);
    return `<div class="pc-timeline" role="img" aria-label="Recorded statements per ${result.granularity}. Maximum ${rawMax} statements in one period. Exact counts follow the chart.">
      <div class="pc-y-axis" aria-hidden="true"><span>${max}</span><span>${Number.isInteger(max/2) ? max/2 : ''}</span><span>0</span></div>
      <div class="pc-time-bars" style="--periods:${periods.length}">${periods.map((p,i)=>`<div class="pc-time-column" title="${esc(p.key)}: ${p.total} statements from ${p.people} profiles; ${esc(countText(p.counts) || 'no recorded statements')}">
        <div class="pc-time-stack" style="height:${percent(p.total,max)}%">${STANCES.filter(s=>p.counts[s]).map(s=>`<span class="pc-fill pc-${s}" style="height:${percent(p.counts[s],p.total)}%"></span>`).join('')}</div>
        ${tickIndexes.includes(i) ? `<span class="pc-time-label ${periods.length===1?'':i===0?'pc-first':i===periods.length-1?'pc-last':''}">${esc(p.label)}</span>` : ''}</div>`).join('')}</div></div>
      <details class="pc-exact"><summary>Exact counts by ${result.granularity}</summary><div class="pc-table-wrap"><table><thead><tr><th>Period</th><th>Statements</th><th>Profiles</th>${STANCES.map(s=>`<th>${LABELS[s]}</th>`).join('')}</tr></thead><tbody>${periods.map(p=>`<tr><th scope="row">${p.key}</th><td>${p.total}</td><td>${p.people}</td>${STANCES.map(s=>`<td>${p.counts[s]}</td>`).join('')}</tr>`).join('')}</tbody></table></div></details>`;
  }

  function groupBreakdowns(members, target, scope='congress') {
    const groups = scope === 'congress' ? Object.entries(PARTIES) : [...new Map(members.map(m=>[m.organization_id,m.organization_name || 'Organization unknown'])).entries()].sort((a,b)=>a[1].localeCompare(b[1]));
    return groups.map(([id,title])=>({...breakdown(members.filter(m=>(scope==='congress' ? party(m.party) : m.organization_id)===id),target),title})).filter(r=>r.total);
  }

  function renderSelected(root, members, target, chartData, facetNames, error, scope='congress') {
    const parties=groupBreakdowns(members,target.id,scope);
    const partyHTML = `<section class="pc-party"><h4>Positions by ${scope === 'congress' ? 'party' : 'organization'}</h4>${parties.length ? parties.map(row=>`<div class="pc-party-row"><span>${esc(row.title)}</span>${stanceBar(row)}</div>`).join('') : '<p>No profiles match these filters.</p>'}${exactTable(parties,scope === 'congress' ? 'Exact counts by party' : 'Exact counts by organization')}</section>`;
    if (!chartData) {
      root.innerHTML=legend()+partyHTML+`<p role="status">${error ? 'Statement charts are unavailable. Reload the page to retry. The profile summaries remain available.' : 'Loading statement charts…'}</p>`;
      return;
    }
    const ids=new Set(members.map(m=>m.id));
    const rows=chartData.policies[target.id].filter(r=>ids.has(r.person_id));
    const history=timeline(rows);
    let html=`${legend()}<div class="pc-detail-grid">${partyHTML}<section><h4>Statements over time</h4>
      ${timelineHTML(history,root.clientWidth>760 ? (root.clientWidth-28)/2 : root.clientWidth)}</section></div>`;
    if (target.facets.length) {
      const cascade = chartData.strategy?.kind === 'confidence_cascade';
      const facets=facetCounts(rows,target.facets).sort((a,b)=>(b.agreed+b.disputed)-(a.agreed+a.disputed));
      const max=Math.max(1,...facets.map(f=>f.agreed+f.disputed));
      html+=`<section class="pc-facets"><h4>Details in these statements</h4>
        <div class="pc-legend"><span><i class="pc-agreed" aria-hidden="true"></i>${cascade ? 'Accepted from DeepSeek' : 'Both models applied the label'}</span><span><i class="${cascade ? 'pc-reviewed' : 'pc-disputed'}" aria-hidden="true"></i>${cascade ? 'Accepted after Astra review' : 'One model applied the label'}</span><span>Shared scale: 0–${max} statements</span></div>
        ${facets.map(f=>`<div class="pc-facet-row"><span>${esc(facetNames[f.id] || f.id)}</span><div class="pc-facet-track" role="img" aria-label="${esc(facetNames[f.id] || f.id)}: ${f.agreed} ${cascade ? 'accepted from DeepSeek' : 'statements tagged by both models'}, ${f.disputed} ${cascade ? 'accepted after Astra review' : 'by one model'}"><span class="pc-agreed" style="width:${percent(f.agreed,max)}%"></span><span class="${cascade ? 'pc-reviewed' : 'pc-disputed'}" style="width:${percent(f.disputed,max)}%"></span></div><span>${f.agreed} ${cascade ? 'first' : 'both'} · ${f.disputed} ${cascade ? 'reviewed' : 'one'}</span></div>`).join('')}</section>`;
    }
    root.innerHTML=html;
  }

  const api={groupBreakdowns,breakdown,timeline,facetCounts,percent,stanceBar,renderOverview,renderSelected};
  if (typeof module !== 'undefined' && module.exports) module.exports=api;
  else global.PolicyCharts=api;
})(typeof window !== 'undefined' ? window : globalThis);
