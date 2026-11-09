/* Federal analysis. The index defines eligibility; each detail file owns its sources. */
(function (global) {
  'use strict';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = value => Number.isInteger(value) ? String(value) : String(Math.round(value * 100) / 100);
  const STANCES = {'-2':'Explicit opposition','-1':'Implied opposition','0':'No stated position','1':'Implied support','2':'Explicit support'};
  const LEVELS = {
    ai_overall:['Mainly a threat','Harms dominate','Balanced','Mainly an opportunity','Enthusiastic'],
    agi_pilled:['Dismisses human-level AI','Ordinary technology','Very large change','Human-level AI is possible','Human-level AI is near'],
    x_risk:['Dismisses the risk','Raises it, plays it down','A real risk','Wants action','A top priority'],
    china_race:['Rejects the race','Mentions the race','One reason among several','The main reason','Outweighs other concerns'],
    regulation:['Opposes rules','Light-touch rules','Targeted rules','Substantial rules','Comprehensive rules']
  };
  const QUESTION_TEXT = {
    ai_overall:'Does AI offer benefits or harms?', agi_pilled:'Will AI reach human-level intelligence?',
    x_risk:'Does catastrophic AI risk need action?', china_race:'How much does competition with China matter?',
    regulation:'How much federal AI regulation?'
  };
  const STATUS = {complete:'Assessment complete',partial:'Some assessments pending',pending:'Assessment pending',no_evidence:'No evidence'};
  const number = value => typeof value === 'number' && Number.isFinite(value);
  const score = value => number(value) && value >= 0 && value <= 4;
  const count = value => Number.isInteger(value) && value >= 0 ? value : 0;
  const quoteID = sid => 'quote-' + encodeURIComponent(sid);

  function safeURL(value) {
    try { const url = new URL(value); return ['https:','http:'].includes(url.protocol) ? url.href : null; }
    catch (_) { return null; }
  }
  function dateLabel(value) {
    if (typeof value !== 'string') return 'Date unknown';
    if (/^\d{4}$/.test(value)) return value + ' (year only)';
    if (/^\d{4}-(0[1-9]|1[0-2])$/.test(value)) return value + ' (day unknown)';
    if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
      const date = new Date(value + 'T00:00:00Z');
      if (Number.isFinite(date.valueOf()) && date.toISOString().slice(0,10) === value) return value;
    }
    return 'Date unknown';
  }
  function filterMembers(members, state = {}, organizations = []) {
    const scope = state.scope === 'institutions' ? 'institution' : 'person';
    const query = String(state.search || '').trim().toLowerCase();
    const descendants = new Set([state.organization]);
    if (state.organization && state.organization !== 'all') {
      let changed = true;
      while (changed) {
        changed = false;
        for (const org of organizations) {
          if (descendants.has(org.parent_id) && !descendants.has(org.id)) { descendants.add(org.id); changed = true; }
        }
      }
    }
    const seen = new Set();
    return (members || []).filter(member => {
      if (!member?.id || seen.has(member.id) || member.entity_type !== scope) return false;
      const ids = [member.organization_id,...(member.organization_ids || [])];
      if (state.organization && state.organization !== 'all' && !ids.some(id => descendants.has(id))) return false;
      if (query && ![member.name,member.organization_name].join(' ').toLowerCase().includes(query)) return false;
      seen.add(member.id);
      return true;
    });
  }
  function scoreState(member, dimension) {
    const detail = member.score_details?.[dimension] || {};
    if (member.status === 'no_evidence' || member.n_statements === 0) return {kind:'no_evidence',value:null,label:'No evidence'};
    if (member.n_labeled < member.n_statements || detail.reason_a === 'pending' || detail.reason_b === 'pending') {
      return {kind:'pending',value:null,label:'Assessment pending'};
    }
    const value = member.scores?.[dimension];
    const reasons = [detail.reason_a,detail.reason_b];
    if (!score(value)) return {kind:'unavailable',value:null,label:
      member.n_statements < 3 || detail.reason_a === 'insufficient_evidence' ? 'Insufficient evidence' :
        reasons.every(reason=>reason === 'no_statements') ? 'No discussion' : 'Score unavailable'};
    const silent = reasons.every(reason => ['silent','no_statements'].includes(reason));
    const meaning = value === 0 && silent ? 'No discussion' : value === 0 && reasons.some(reason=>!reason || ['silent','no_statements'].includes(reason)) ? null :
      Number.isInteger(value) ? LEVELS[dimension]?.[value] : null;
    return {kind:'scored',value,label:fmt(value) + (meaning ? ' · ' + meaning : ''),silent:value === 0 && silent};
  }
  function scoreDistribution(members, dimension) {
    const result = {total:members.length,scored:0,pending:0,no_evidence:0,unavailable:0,
      bins:[0,1,2,3,4].map(value => ({score:value,label:String(value),count:0}))};
    for (const member of members) {
      const value = scoreState(member,dimension);
      result[value.kind]++;
      if (value.kind === 'scored') result.bins[Math.round(value.value)].count++;
    }
    return result;
  }
  function validateDetail(detail, member, data) {
    if (detail?.schema_version !== 1 || !data.revision || detail.revision !== data.revision || detail.id !== member.id ||
        detail.profile?.id !== member.id || !data.members.some(m => m.id === member.id) ||
        !Array.isArray(detail.statements) || detail.statements.length !== member.n_statements ||
        detail.statements.some(s => !s?.sid) || new Set(detail.statements.map(s => s.sid)).size !== detail.statements.length ||
        !Array.isArray(detail.history) || !Array.isArray(detail.changes)) {
      throw new Error('Missing or stale profile data. Reload the page to get the latest export.');
    }
    return detail;
  }
  function citations(sids, statements) {
    const available = new Set(statements.map(s => s.sid));
    const ids = [...new Set(Array.isArray(sids) ? sids : [])];
    const links = ids.filter(sid => available.has(sid)).map(sid =>
      `<a class="fa-citation" href="#${esc(quoteID(sid))}" data-quote="${esc(sid)}" aria-label="Read source quote ${esc(sid)}">${esc(sid)}</a>`).join(' ');
    const missing = ids.some(sid => !available.has(sid));
    return links + (missing ? '<span class="fa-warning">Unavailable citation</span>' : '');
  }
  function renderSummary(summary, statements) {
    if (summary?.status === 'no_evidence') return '<p class="fa-empty">No verified statements support a summary yet.</p>';
    if (summary?.status !== 'complete' || !summary.text) return '<p class="fa-empty">Summary pending. Source quotes remain available below.</p>';
    if (Array.isArray(summary.sentences) && summary.sentences.length) {
      return `<p class="fa-summary-text">${summary.sentences.map(sentence=>`${esc(sentence.text)} <span class="fa-citations">${citations(sentence.sids,statements)}</span>`).join(' ')}</p>`;
    }
    return `<p class="fa-summary-text">${esc(summary.text)}</p><p class="fa-citations">${citations(summary.sids,statements)}</p>`;
  }
  function renderRegulation(regulation, areas, statements) {
    const ready = regulation?.status === 'complete';
    const noEvidence = regulation?.status === 'no_evidence';
    let group = null;
    const rows = areas.map(area => {
      const entry = regulation?.areas?.[area.id];
      const valid = ready && (!entry || Object.hasOwn(STANCES,String(entry.stance)));
      const value = valid ? entry?.stance || 0 : null;
      const heading = area.group !== group ? `<tr class="fa-group-row"><th colspan="3" scope="rowgroup">${esc(area.group || 'AI rules')}</th></tr>` : '';
      group = area.group;
      const label = noEvidence ? 'No evidence' : valid ? STANCES[value] : 'Assessment pending';
      return `${heading}<tr><th scope="row">${esc(area.title)}</th><td><span class="fa-stance ${value > 0 ? 'fa-support' : value < 0 ? 'fa-oppose' : ''}">${esc(label)}</span></td>
        <td>${valid && value ? `<p>${esc(entry.why || '')}</p><span class="fa-citations">${citations(entry.sids,statements)}</span>` : '<span class="fa-muted">—</span>'}</td></tr>`;
    }).join('');
    return `<div class="fa-table-scroll"><table class="fa-regulation-table"><caption class="fa-sr-only">Positions on ${areas.length} types of AI rules</caption><thead><tr><th scope="col">Type of rule</th><th scope="col">Position</th><th scope="col">Reason and sources</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }
  function reasonLabel(reason) {
    const text = {silent:'No discussion in the assessed statements.', no_statements:'No statement addresses this question.',
      dismissive:'The statements reject this claim.',consistent:'At least two statements reach this level.',
      one_off_capped:'Only one statement reaches the highest level; the formula lowers the score by one.',
      insufficient_evidence:'The profile needs at least three statements.',pending:'Assessment pending.'};
    if (/^median_of_\d+$/.test(reason || '')) return `The median uses ${reason.split('_').pop()} relevant statements.`;
    return text[reason] || reason || 'No reason available.';
  }
  function renderScores(member, dimensions, statements) {
    return `<div class="fa-profile-scores">${dimensions.map(d => {
      const value = scoreState(member,d.id), detail = member.score_details?.[d.id] || {};
      const meaning = value.kind === 'scored' ? value.label.includes(' · ') ? value.label.split(' · ').slice(1).join(' · ') : 'Mean of available assessments' : value.label;
      return `<section><h3>${esc(d.title)}</h3><p style="--score-color:${value.kind==='scored' ? `var(--r${Math.round(value.value)})` : 'var(--nodata)'}" class="fa-score ${value.kind === 'scored' ? '' : 'fa-score-missing'}">${value.kind === 'scored' ? fmt(value.value) : '—'}</p>
        <p class="fa-score-label">${esc(meaning)}</p>
        <details class="fa-score-reasons"><summary>Score details</summary><p>Assessment A: ${esc(reasonLabel(detail.reason_a))}</p><p>Assessment B: ${esc(reasonLabel(detail.reason_b))}</p>
        <p>${count(detail.label_count)} relevant labels.</p><p class="fa-citations">${citations(detail.sids,statements)}</p></details></section>`;
    }).join('')}</div>`;
  }
  function renderStatement(statement, dimensions) {
    const analysis = statement.analysis || {}, attribution = statement.attribution;
    const source = safeURL(statement.url), complete = analysis.status === 'complete';
    const modelNames = Object.entries(analysis.models || {}).filter(([,value]) => value).map(([key,value]) => `${esc(key)}: ${esc(value)}`).join(' · ');
    const label = (assessment, id) => score(assessment?.[id]) ? fmt(assessment[id]) : 'Not discussed';
    const rows = dimensions.map(d => `<tr><th scope="row">${esc(d.title)}</th><td>${complete && analysis.a ? label(analysis.a,d.id) : 'Pending'}</td>
      <td>${complete && analysis.b ? label(analysis.b,d.id) : 'Pending'}</td><td>${number(analysis.confidence?.[d.id]) ? esc(analysis.confidence[d.id]) + ' of 5' : '—'}</td></tr>`).join('');
    const escalated = Array.isArray(analysis.escalated) ? analysis.escalated : [];
    const escalatedNames = escalated.map(id => dimensions.find(d => d.id === id)?.title || id);
    return `<article class="fa-quote" id="${esc(quoteID(statement.sid))}" tabindex="-1"><div class="fa-quote-meta"><span class="fa-source-id">${esc(statement.sid)}</span>
      <span>${esc(dateLabel(statement.date))} · ${esc(statement.source_type || 'Source type unknown')}</span>
      ${source ? `<a href="${esc(source)}" target="_blank" rel="noopener noreferrer">Read source <span aria-hidden="true">↗</span></a>` : '<span class="fa-muted">Source link unavailable</span>'}</div>
      ${attribution ? `<p class="fa-attribution"><strong>${esc({personal:'Personal statement',official_role:'Official role',institutional:'Institutional statement'}[attribution.kind] || 'Attribution')}:</strong> ${esc(attribution.speaker || '')}${attribution.role ? ' · ' + esc(attribution.role) : ''}${attribution.note ? '. ' + esc(attribution.note) : ''}</p>` : '<p class="fa-attribution">Attribution context unavailable.</p>'}
      <blockquote>${esc(statement.text)}</blockquote><p class="fa-quote-topics">${(analysis.topics || []).map(t => `<span>${esc(t)}</span>`).join('')}</p>
      <details class="fa-assessment"><summary>${complete ? 'Assessment details' : 'Assessment pending'}</summary>
      <p class="fa-note">The two label columns feed the score formula. Confidence uses a model scale from 1 to 5; it does not measure accuracy.</p>
      <div class="fa-table-scroll"><table><caption class="fa-sr-only">Statement assessments for ${esc(statement.sid)}</caption><thead><tr><th scope="col">Question</th><th scope="col">A</th><th scope="col">B</th><th scope="col">Confidence</th></tr></thead><tbody>${rows}</tbody></table></div>
      ${escalatedNames.length ? `<p>Independent review: ${esc(escalatedNames.join(', '))}.</p>` : ''}${modelNames ? `<p class="fa-models">Model configuration: ${modelNames}</p>` : ''}</details></article>`;
  }
  function historySeries(history, dimension, kind) {
    return (history || []).filter(row => row.kind === kind && /^\d{4}-\d{2}-\d{2}$/.test(row.date || '') && dateLabel(row.date) !== 'Date unknown')
      .sort((a,b) => a.date.localeCompare(b.date)).map(row => ({...row,
        value:row.status === 'complete' && score(row.scores?.[dimension]) ? row.scores[dimension] : null}));
  }
  function historyChart(rows, dimension, kind, title) {
    const width = 640, height = 220, left = 34, right = 18, top = 18, bottom = 34;
    const times = rows.map(row => Date.parse(row.date + 'T00:00:00Z'));
    const start = times[0], span = times[times.length-1] - start || 1;
    const x = index => rows.length === 1 ? (left + width - right) / 2 : left + (times[index]-start) / span * (width-left-right);
    const y = value => top + (4-value) / 4 * (height-top-bottom);
    const segments = []; let segment = [];
    rows.forEach((row,i) => { if (row.value === null) { if (segment.length) segments.push(segment); segment = []; }
      else segment.push([x(i),y(row.value)]); });
    if (segment.length) segments.push(segment);
    const points = rows.map((row,i) => row.value === null ? '' : `<circle cx="${x(i).toFixed(2)}" cy="${y(row.value).toFixed(2)}" r="3.5"><title>${esc(row.date)}: ${fmt(row.value)}</title></circle>`).join('');
    const id = 'fa-history-' + kind + '-' + dimension;
    return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="${esc(id)}" class="fa-history-chart"><title id="${esc(id)}">${esc(title)}. ${rows.length} records. The exact values appear in the table below.</title>
      ${[0,1,2,3,4].map(value => `<line class="fa-grid" x1="${left}" y1="${y(value)}" x2="${width-right}" y2="${y(value)}"/><text x="${left-12}" y="${y(value)+4}" text-anchor="end">${value}</text>`).join('')}
      ${kind === 'reconstructed' ? segments.map(points => `<polyline points="${points.map(p=>p.map(n=>n.toFixed(2)).join(',')).join(' ')}"/>`).join('') : ''}${points}
      <text x="${left}" y="${height-8}">${esc(rows[0].date)}</text>${rows.length > 1 ? `<text x="${width-right}" y="${height-8}" text-anchor="end">${esc(rows[rows.length-1].date)}</text>` : ''}</svg>`;
  }
  function renderHistory(history, dimension, title) {
    return `<p class="fa-note">Reconstructed history applies today's labels to evidence available by each month-end. It tracks today's eligible roster, not historical membership.</p>
      <p class="fa-note">Partial dates enter after their full date range ends. Undated statements stay out. No discussion can produce a zero; so can the rubric's lowest position.</p>
      ${['reconstructed','observed'].map(kind => {
        const rows = historySeries(history,dimension,kind), label = kind === 'reconstructed' ? 'Reconstructed history' : 'Observed snapshots';
        return `<section class="fa-history-kind"><h4>${label}</h4><p class="fa-note">${kind === 'observed' ? 'These snapshots record the scores that the update process produced on those dates.' : 'The line shows an estimate from available dated statements. Gaps mark unavailable scores.'}</p>
          ${rows.length ? `${historyChart(rows,dimension,kind,title + ': ' + label)}<details><summary>Exact dates and scores (${rows.length})</summary><div class="fa-table-scroll"><table><thead><tr><th scope="col">Date</th><th scope="col">Score</th><th scope="col">Statements</th></tr></thead><tbody>${rows.map(row => `<tr><td>${esc(row.date)}</td><td>${row.value === null ? row.status === 'partial' || row.status === 'pending' ? 'Assessment pending' : row.n_statements < 3 ? 'Insufficient evidence' : 'No score' : fmt(row.value)}</td><td>${count(row.n_statements)}</td></tr>`).join('')}</tbody></table></div></details>` : `<p class="fa-empty">No ${label.toLowerCase()} available.</p>`}</section>`;
      }).join('')}`;
  }
  function renderDistribution(members, dimensions) {
    return `<div class="fa-distributions">${dimensions.map(d => {
      const result = scoreDistribution(members,d.id), max = Math.max(1,...result.bins.map(b=>b.count));
      const title = `Distribution for ${d.title}: ${result.scored} of ${result.total} profiles have scores.`;
      return `<section class="fa-distribution"><h3>${esc(d.title)}</h3><p class="fa-dim-question">${esc(QUESTION_TEXT[d.id] || '')}</p>
        <svg viewBox="0 0 200 140" role="img" aria-label="${esc(title)}"><line class="fa-grid" x1="10" y1="112" x2="194" y2="112"/>
          ${result.bins.map((bin,i) => { const h=bin.count / max * 82, x=13+i*37; return `<rect class="fa-bin-${i}" x="${x}" y="${112-h}" width="27" height="${h}"><title>${esc(bin.label)}: ${bin.count} profiles</title></rect><text x="${x+13.5}" y="${Math.min(105,105-h)}" text-anchor="middle">${bin.count}</text><text class="fa-axis-label" x="${x+13.5}" y="132" text-anchor="middle">${esc(bin.label)}</text>`; }).join('')}</svg>
        <p class="fa-denominator"><strong>${result.scored}</strong> of ${result.total} profiles have scores</p>
        <p class="fa-note">${result.pending} pending · ${result.no_evidence} no evidence · ${result.unavailable} other unscored</p>
        <details><summary>Exact counts and scale</summary><table><thead><tr><th scope="col">Score band</th><th scope="col">Profiles</th></tr></thead><tbody>${result.bins.map(b=>`<tr><td>${esc(b.label)}</td><td>${b.count}</td></tr>`).join('')}</tbody></table><p class="fa-note">${(LEVELS[d.id] || []).map((label,i)=>`${i}: ${esc(label)}`).join('. ')}. No discussion can also score zero.</p></details></section>`;
    }).join('')}</div>`;
  }
  function renderTopics(member, topics) {
    const counts = topics.map(topic => ({topic,total:number(member.topics?.[topic]) && member.topics[topic] >= 0 ? member.topics[topic] : 0}));
    const max = Math.max(1,...counts.map(row=>row.total));
    return `<p class="fa-note">Topic totals show statement shares across ${count(member.n_labeled)} assessed statements. Each statement's weight is split equally among its topics.${member.n_labeled < member.n_statements ? ' Unfinished assessments can change these totals.' : ''}</p>
      <div class="fa-topics">${counts.map(row=>`<div class="fa-topic"><span>${esc(row.topic)}</span><div class="fa-topic-track" aria-hidden="true"><span style="width:${row.total/max*100}%"></span></div><strong>${fmt(row.total)}</strong></div>`).join('')}</div>`;
  }
  function renderChanges(changes, dimensions, statements) {
    if (!changes?.length) return '<p class="fa-note">No observed score changes recorded.</p>';
    return `<details class="fa-changes"><summary>Observed score changes (${changes.length})</summary><div class="fa-table-scroll"><table><thead><tr><th scope="col">Date</th><th scope="col">Question</th><th scope="col">Change</th><th scope="col">Cause and sources</th></tr></thead><tbody>${changes.map(change=>`<tr><td>${esc(dateLabel(change.date))}</td><th scope="row">${esc(dimensions.find(d=>d.id===change.dimension)?.title || change.dimension)}</th><td>${score(change.old) ? fmt(change.old) : 'Unavailable'} → ${score(change.new) ? fmt(change.new) : 'Unavailable'}</td><td>${esc(change.cause || 'Cause not recorded')} ${citations(change.sids,statements)}</td></tr>`).join('')}</tbody></table></div></details>`;
  }
  async function mount(root) {
    if (!root) return;
    let data;
    try {
      const response = await fetch('data/federal_analysis.json');
      if (!response.ok) throw new Error('Export unavailable');
      data = await response.json();
      if (data.schema_version !== 1 || !data.revision || !Array.isArray(data.members) || !Array.isArray(data.dimensions) || !Array.isArray(data.regulation_areas)) throw new Error('Invalid export');
    } catch (_) {
      root.innerHTML = '<div class="fa-empty" role="status"><h2>Federal analysis is unavailable</h2><p>The export is missing or incomplete. Please reload the page later.</p><a href="index.html#policy-section">Open the policy explorer</a></div>';
      return;
    }
    const params = new URLSearchParams(global.location?.search || '');
    const initial = data.members.find(m=>m.id===params.get('profile'));
    const charts=global.FederalCharts;
    let chartData=null,chartError='';
    try {
      const response=await fetch('data/federal_charts.json');
      if (!response.ok) throw new Error('History and topic chart data are unavailable. Reload the page to try again.');
      chartData=charts.validateCharts(await response.json(),data);
    } catch(error) {chartError=error.message;}
    const state = {scope:initial?.entity_type === 'institution' || params.get('scope') === 'institutions' ? 'institutions' : 'officials',
      organization:'all',search:'',selected:initial?.id || null,dimension:data.dimensions[0]?.id,page:0,
      chartDimension:'x_risk',compare:'regulation',historyKind:'reconstructed',topic:data.topics[0],range:'12m',preset:'agi_low_risk',rule:null};
    let request = 0, currentDetail = null;
    const cache = new Map();
    const dimensionOptions=id=>data.dimensions.map(d=>`<option value="${esc(d.id)}" ${d.id===id?'selected':''}>${esc(d.title)}</option>`).join('');
    root.innerHTML = `<nav class="fc-toc" aria-label="Federal analysis sections"><a href="#fc-cohort">Profiles by score</a><a href="#fc-comparison">Compare scores</a><a href="#fc-agency-section">Scores by agency</a><a href="#fc-timeline-section">Scores over time</a><a href="#fc-recent-section">Recent changes</a><a href="#fc-policy-section">Policies they support</a><a href="#fc-topic-section">Topics</a><a href="#fc-groups-section">Profile groups</a><a href="#fc-members-section">All profiles</a><a href="#fa-profiles">Sources and history</a></nav>
      <section class="fc-controlbar" aria-label="Chart controls"><label>Question <select id="fc-dimension">${dimensionOptions(state.chartDimension)}</select></label><div class="fa-scope" role="group" aria-label="Profile type"><button type="button" data-scope="officials" aria-pressed="true">Executive officials</button><button type="button" data-scope="institutions" aria-pressed="false">Institutions</button></div></section>
      <section class="fa-filter-section" aria-label="Filter federal profiles">
      <div class="fa-filters"><label>Agency or membership<select id="fa-agency"><option value="all">All organizations</option>${(data.organizations || []).map(o=>`<option value="${esc(o.id)}">${esc(o.name)}</option>`).join('')}</select></label><label>Name or organization<input id="fa-search" type="search" placeholder="Search profiles" autocomplete="off"></label></div>
      <p class="fa-note">Agency filters include subagencies and linked roles. Each profile counts once. Officials and institutions have separate totals.</p></section>
      <div id="fa-coverage" class="fa-coverage" aria-live="polite"></div>
      <section class="fc-section" id="fc-cohort"><h2 id="fc-cohort-title">Federal profiles by score</h2><p class="fc-description">Each dot is one profile. Colors show the selected score, from low to high. Select a dot to read its evidence.</p><div id="fc-dots"></div><p class="fa-note">Colors round scores to the nearest whole number, as on the Congress page. A zero can mean no discussion. Gray means unscored.</p></section>
      <section class="fc-section" id="fc-comparison"><div class="fa-section-heading"><h2>Compare two AI scores</h2><label class="fc-control">Vertical axis<select id="fc-compare">${dimensionOptions(state.compare)}</select></label></div><p class="fc-description" id="fc-scatter-description"></p><div id="fc-scatter"></div></section>
      <section class="fc-section" id="fc-agency-section"><h2>Scores by agency</h2><p class="fc-description">Each bar includes all selected profiles in that agency. Select a bar to see its profiles.</p><div id="fc-agencies"></div><p class="fa-note">Primary affiliation determines each group. Subagencies roll up to their parent. Linked roles do not add a second count.</p><div id="fc-agency-selection" aria-live="polite"></div></section>
      <section class="fc-section" id="fc-timeline-section"><div class="fa-section-heading"><h2>Profiles scoring 3 or more over time</h2><label class="fc-control">History<select id="fc-history-kind"><option value="reconstructed">Monthly reconstruction</option><option value="observed">Observed snapshots</option></select></label></div><p class="fc-description">The share uses all selected profiles, including those without scores. Earlier coverage is often thinner.</p><div id="fc-timeline"></div><p class="fa-note">Reconstruction applies current labels to dated evidence for today's eligible roster. It does not track historical office membership. Observed snapshots stay separate.</p></section>
      <section class="fc-section" id="fc-recent-section"><h2>Recent score changes</h2><p class="fc-description">Observed changes in the selected question over the past 60 days.</p><div id="fc-recent"></div></section>
      <section class="fc-section" id="fc-policy-section"><h2>Which AI policies they support</h2><p class="fc-description">Bars extend left for opposition and right for support. Select a policy to see the profiles behind each position.</p><div id="fc-policies"></div><div id="fc-policy-selection" aria-live="polite"></div></section>
      <section class="fc-section" id="fc-topic-section"><div class="fa-section-heading"><h2>What they talk about</h2><label class="fc-control">Time range<select id="fc-range"><option value="3m">3 months</option><option value="12m" selected>12 months</option><option value="all">All time</option></select></label></div><p class="fc-description">Topic shares use a rolling 30-day window. Each statement divides its weight equally among its topics.</p><div id="fc-topic-share"></div><p class="fa-note">Partial dates enter at the end of their month or year. Undated and unfinished statements stay out. Gaps mean no dated statements.</p><div class="fa-section-heading fc-voices-heading"><h3>Top voices on a topic</h3><label class="fc-control">Topic<select id="fc-topic">${data.topics.map(t=>`<option>${esc(t)}</option>`).join('')}</select></label></div><p class="fa-note">The top 15 profiles by statement share across all assessed evidence, including undated statements. Select a name to read its sources.</p><div id="fc-voices"></div></section>
      <section class="fc-section" id="fc-groups-section"><h2>Profile groups</h2><p class="fc-description">Find profiles with a particular combination of views. High means at least 3; low means below 2.</p><div class="fc-presets">${charts.PRESETS.map(p=>`<button type="button" data-preset="${p.id}" aria-pressed="${p.id===state.preset}">${esc(p.title)}</button>`).join('')}</div><p class="fa-note">Low scores can reflect silence. Open each profile to check the explanation and sources.</p><div id="fc-group-members" class="fc-profile-chips" aria-live="polite"></div></section>
      <section class="fc-section" id="fc-members-section"><h2>All profiles</h2><p class="fc-description">Compare the five scores and open the evidence for any profile in this view.</p><div id="fc-members"></div></section>
      <section class="fa-overview" aria-labelledby="fa-overview-title"><div class="fa-section-heading"><div><p class="fa-eyebrow">The current cohort</p><h2 id="fa-overview-title">Five questions about AI</h2></div><a href="#fa-profiles">Explore a profile ↓</a></div>
      <p class="fa-note">Bars count profiles by the nearest whole score. Missing evidence and unfinished labels stay outside the bars.</p><div id="fa-distributions"></div></section>
      <section id="fa-profiles" class="fa-profile-section" aria-labelledby="fa-profile-section-title"><div class="fa-section-heading"><div><p class="fa-eyebrow">Evidence behind the scores</p><h2 id="fa-profile-section-title">Explore a profile</h2></div></div>
      <div class="fa-explorer"><aside class="fa-profile-picker"><label for="fa-profile-choice">Choose a profile</label><select id="fa-profile-choice"></select><p id="fa-profile-count" class="fa-note"></p><div id="fa-profile-list" class="fa-profile-list" aria-label="Profiles"></div></aside><div id="fa-profile-panel" class="fa-profile-panel" aria-live="polite"></div></div></section>
      <section class="fa-method" id="method"><p class="fa-eyebrow">How to read this page</p><h2>Sources, scores, and limits</h2><p>${esc(data.methodology?.text || 'The analysis uses verified public statements, model labels, and a fixed score formula.')}</p>
      <p>A profile needs at least three statements for a score. A zero can mean no discussion or the lowest rubric position. Score details explain the result.</p>
      <p>Institutional statements describe the institution. They do not establish an official's personal views. Officials' views do not establish institutional positions.</p>
      <p>These records cover today's eligible federal roster. Search completion does not establish complete evidence or equal evidence depth.</p>
      <p class="fa-models">${esc(Object.entries(data.methodology?.models || {}).map(([key,value])=>`${key}: ${value}`).join(' · '))}</p>
      <p><a href="data/federal_analysis.json" download>Download the analysis index (JSON)</a> · <a href="index.html#policy-section">Explore named policies</a></p><p class="fa-note">Export built ${esc(dateLabel(data.built_on?.slice(0,10)))}.</p></section>`;
    const get = id => root.querySelector('#' + id);
    const selectedMembers=()=>filterMembers(data.members,state,data.organizations || []).sort((a,b)=>a.name.localeCompare(b.name));
    function renderCharts() {
      const members=selectedMembers(),dim=data.dimensions.find(d=>d.id===state.chartDimension),profiles=chartData?.profiles;
      get('fc-cohort-title').textContent=`${state.scope==='institutions'?'Institutions':'Officials'} by ${dim.title} score`;
      get('fc-dots').innerHTML=charts.renderDots(members,state.chartDimension);
      get('fc-scatter-description').textContent=`Horizontal axis: ${dim.title}. Vertical axis: ${data.dimensions.find(d=>d.id===state.compare).title}.`;
      get('fc-scatter').innerHTML=charts.renderScatter(members,state.chartDimension,state.compare,data.dimensions);
      get('fc-agencies').innerHTML=charts.renderAgencies(members,state.chartDimension,data.organizations || []);
      get('fc-agency-selection').innerHTML='';
      const unavailable=`<p class="fa-empty" role="status">${esc(chartError)}</p>`;
      get('fc-timeline').innerHTML=profiles?charts.renderTimeline(members,profiles,state.chartDimension,state.historyKind):unavailable;
      get('fc-recent').innerHTML=profiles?charts.renderRecent(members,profiles,state.chartDimension,data.built_on.slice(0,10)):unavailable;
      get('fc-policies').innerHTML=charts.renderPolicies(members,data.regulation_areas,state.rule);
      get('fc-policy-selection').innerHTML=charts.renderPolicySelection(members,data.regulation_areas,state.rule);
      get('fc-topic-share').innerHTML=profiles?charts.renderTopicShare(members,profiles,data.topics,state.range,data.built_on.slice(0,10)):unavailable;
      get('fc-voices').innerHTML=charts.renderVoices(members,state.topic);
      renderGroup();
      get('fc-members').innerHTML=charts.renderMembers(members,data.dimensions);
    }
    function renderGroup() {
      root.querySelectorAll('[data-preset]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.preset===state.preset)));
      const members=charts.presetMembers(selectedMembers(),state.preset);
      get('fc-group-members').innerHTML=members.length?members.map(m=>`<a href="#fa-profiles" data-chart-profile data-profile="${esc(m.id)}">${esc(m.name)}</a>`).join(''):'<p class="fa-empty">No profiles in this view meet these score thresholds.</p>';
    }
    function updateURL() {
      if (!global.history?.replaceState) return;
      const url = new URL(global.location.href);
      url.searchParams.set('scope',state.scope);
      if (state.selected) url.searchParams.set('profile',state.selected); else url.searchParams.delete('profile');
      url.hash = '';
      global.history.replaceState(null,'',url);
    }
    function renderSources() {
      if (!currentDetail) return;
      const sources = currentDetail.statements, pages = Math.max(1,Math.ceil(sources.length/20));
      state.page = Math.min(state.page,pages-1);
      get('fa-sources').innerHTML = sources.length ? sources.slice(state.page*20,(state.page+1)*20).map(s=>renderStatement(s,data.dimensions)).join('') : '<p class="fa-empty">No verified statements in this profile.</p>';
      get('fa-source-pages').innerHTML = sources.length > 20 ? `<button type="button" data-source-page="${state.page-1}" ${state.page===0 ? 'disabled' : ''}>Previous quotes</button><span>Page ${state.page+1} of ${pages}</span><button type="button" data-source-page="${state.page+1}" ${state.page===pages-1 ? 'disabled' : ''}>Next quotes</button>` : '';
    }
    function renderProfile(member, detail) {
      const statements = detail.statements;
      get('fa-profile-panel').innerHTML = `<header class="fa-profile-header"><p class="fa-eyebrow">${member.entity_type === 'institution' ? 'Institution' : 'Executive official'} · ${esc(member.organization_name || 'Organization not listed')}</p>
        <h3 id="fa-profile-name" tabindex="-1">${esc(member.name)}</h3><p>${count(member.n_statements)} verified statements · ${count(member.n_labeled)} assessed · <span class="fa-status">${esc(STATUS[member.status] || 'Assessment pending')}</span></p>
        <p class="fa-note">${member.entity_type === 'institution' ? 'This profile uses institutional statements. Its positions do not transfer to its members.' : "This profile uses this official's statements. Agency positions do not transfer to this official."}</p></header>
        <nav class="fa-profile-nav" aria-label="Profile sections"><a href="#fa-summary">Summary</a><a href="#fa-rules">AI rules</a><a href="#fa-history">History</a><a href="#fa-source-section">Sources</a></nav>
        ${renderScores(member,data.dimensions,statements)}
        <section id="fa-summary" class="fa-profile-block"><h3>What the evidence says</h3>${renderSummary(member.summary,statements)}</section>
        <section class="fa-profile-block"><h3>Topics in the statements</h3>${renderTopics(member,data.topics || [])}</section>
        <section id="fa-rules" class="fa-profile-block"><h3>Positions on ${data.regulation_areas.length} types of AI rules</h3><p class="fa-note">A stated harm alone does not establish support for a rule. No stated position does not mean opposition.</p>${renderRegulation(member.regulation,data.regulation_areas,statements)}</section>
        <section id="fa-history" class="fa-profile-block"><div class="fa-section-heading"><h3>Scores over time</h3><label class="fa-history-choice">Question<select id="fa-history-dimension">${data.dimensions.map(d=>`<option value="${esc(d.id)}" ${state.dimension===d.id ? 'selected' : ''}>${esc(d.title)}</option>`).join('')}</select></label></div><div id="fa-history-content"></div>${renderChanges(detail.changes,data.dimensions,statements)}</section>
        <section id="fa-source-section" class="fa-profile-block"><div class="fa-section-heading"><h3>Source quotes</h3><a href="data/federal_analysis/${encodeURIComponent(member.id)}.json" download>Download profile (JSON)</a></div><p class="fa-note">Quotes retain their source dates and attribution. Assessment details show the labels, confidence, and model IDs.</p><div id="fa-sources"></div><div id="fa-source-pages" class="fa-pages"></div></section>`;
      get('fa-history-content').innerHTML = renderHistory(detail.history,state.dimension,data.dimensions.find(d=>d.id===state.dimension)?.title || 'Score');
      renderSources();
    }
    async function loadProfile(member) {
      const token = ++request;
      currentDetail = null;
      get('fa-profile-panel').setAttribute('aria-busy','true');
      get('fa-profile-panel').innerHTML = '<p class="fa-empty" role="status">Load source quotes and analysis…</p>';
      try {
        let detail = cache.get(member.id);
        if (!detail) {
          const response = await fetch(`data/federal_analysis/${encodeURIComponent(member.id)}.json`);
          if (!response.ok) throw new Error('Profile sources are unavailable. Please try again later.');
          detail = validateDetail(await response.json(),member,data);
          cache.set(member.id,detail);
        }
        if (token !== request) return;
        currentDetail = detail;
        renderProfile(member,detail);
      } catch (error) {
        if (token !== request) return;
        get('fa-profile-panel').innerHTML = `<div class="fa-empty" role="status"><h3>${esc(member.name)}</h3><p>${esc(error.message)}</p><p>Unavailable data does not establish a position.</p><button type="button" data-retry>Retry this profile</button></div>`;
      } finally { if (token === request) get('fa-profile-panel').setAttribute('aria-busy','false'); }
    }
    function render(skipCharts=false) {
      const members = filterMembers(data.members,state,data.organizations || []).sort((a,b)=>a.name.localeCompare(b.name));
      if (!members.some(m=>m.id===state.selected)) state.selected = members[0]?.id || null;
      root.querySelectorAll('[data-scope]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.scope===state.scope)));
      const assessed = members.reduce((n,m)=>n+count(m.n_labeled),0), total = members.reduce((n,m)=>n+count(m.n_statements),0);
      get('fa-coverage').innerHTML = `<div><strong>${members.length}</strong><span>${state.scope === 'institutions' ? 'institutions' : 'officials'} in this view</span></div><div><strong>${total.toLocaleString()}</strong><span>verified statements</span></div><div><strong>${assessed.toLocaleString()}</strong><span>statements assessed</span></div><div><strong>${members.filter(m=>m.status==='partial').length}</strong><span>profiles with unfinished work</span></div>`;
      get('fa-distributions').innerHTML = renderDistribution(members,data.dimensions);
      if (!skipCharts) renderCharts();
      get('fa-profile-choice').innerHTML = members.length ? members.map(m=>`<option value="${esc(m.id)}" ${m.id===state.selected ? 'selected' : ''}>${esc(m.name)}</option>`).join('') : '<option>No matching profiles</option>';
      get('fa-profile-choice').disabled = !members.length;
      get('fa-profile-count').textContent = members.length + ' matching profiles';
      get('fa-profile-list').innerHTML = members.map(m=>`<button type="button" data-profile="${esc(m.id)}" aria-pressed="${m.id===state.selected}"><span>${esc(m.name)}</span><small>${esc(m.organization_name || '')}</small><span class="fa-list-count">${count(m.n_statements)} quotes${m.status==='partial' ? ' · pending' : m.status==='no_evidence' ? ' · no evidence' : ''}</span></button>`).join('');
      updateURL();
      const selected = members.find(m=>m.id===state.selected);
      state.page = 0;
      if (selected) loadProfile(selected);
      else { request++; currentDetail=null; get('fa-profile-panel').innerHTML='<p class="fa-empty">No profiles match these filters. Change the name or agency filter.</p>'; get('fa-profile-panel').setAttribute('aria-busy','false'); }
    }
    get('fa-agency').addEventListener('change',event=>{ state.organization=event.target.value; render(); });
    get('fa-search').addEventListener('input',event=>{ state.search=event.target.value; render(); });
    get('fa-profile-choice').addEventListener('change',event=>{ state.selected=event.target.value; render(true); });
    root.addEventListener('change',event=>{
      const controls={'fc-dimension':'chartDimension','fc-compare':'compare','fc-history-kind':'historyKind','fc-range':'range','fc-topic':'topic'};
      if(controls[event.target.id]) {state[controls[event.target.id]]=event.target.value;renderCharts();return;}
      if (event.target.id === 'fa-history-dimension' && currentDetail) { state.dimension=event.target.value; get('fa-history-content').innerHTML=renderHistory(currentDetail.history,state.dimension,data.dimensions.find(d=>d.id===state.dimension)?.title || 'Score'); }
    });
    root.addEventListener('click',event=>{
      const scope = event.target.closest('[data-scope]');
      if (scope) { state.scope=scope.dataset.scope; state.selected=null; render(); return; }
      const profile = event.target.closest('[data-profile]');
      if (profile) { event.preventDefault();state.selected=profile.dataset.profile; render(true);if(profile.hasAttribute('data-chart-profile')) get('fa-profiles').scrollIntoView({block:'start'});return; }
      const preset=event.target.closest('[data-preset]');
      if(preset) {state.preset=preset.dataset.preset;renderGroup();return;}
      const rule=event.target.closest('[data-rule]');
      if(rule) {state.rule=rule.dataset.rule;get('fc-policies').innerHTML=charts.renderPolicies(selectedMembers(),data.regulation_areas,state.rule);get('fc-policy-selection').innerHTML=charts.renderPolicySelection(selectedMembers(),data.regulation_areas,state.rule);get('fc-policy-selection').scrollIntoView({block:'center'});return;}
      const agency=event.target.closest('[data-agency-group]');
      if(agency) {
        const group=charts.agencyDistribution(selectedMembers(),state.chartDimension,data.organizations || []).find(g=>g.id===agency.dataset.agencyGroup);
        get('fc-agency-selection').innerHTML=`<h3>${esc(group.name)}</h3><div class="fc-profile-chips">${group.members.map(m=>`<a href="#fa-profiles" data-profile="${esc(m.id)}" data-chart-profile>${esc(m.name)}</a>`).join('')}</div>`;
        return;
      }
      const retry = event.target.closest('[data-retry]');
      if (retry) { const member=data.members.find(m=>m.id===state.selected); if (member) loadProfile(member); return; }
      const page = event.target.closest('[data-source-page]');
      if (page && currentDetail) { state.page=Math.max(0,Number(page.dataset.sourcePage)); renderSources(); get('fa-source-section').scrollIntoView({block:'start'}); return; }
      const quote = event.target.closest('[data-quote]');
      if (quote && currentDetail) {
        event.preventDefault();
        const index = currentDetail.statements.findIndex(s=>s.sid===quote.dataset.quote);
        if (index < 0) return;
        state.page=Math.floor(index/20); renderSources();
        const target = document.getElementById(quoteID(quote.dataset.quote));
        target?.scrollIntoView({block:'start'}); target?.focus({preventScroll:true});
      }
    });
    render();
    const hero=document.querySelector('.fa-hero'),toc=root.querySelector('.fc-toc');
    if (hero && 'IntersectionObserver' in global) {
      new IntersectionObserver(entries=>{toc.style.visibility=entries[0].isIntersecting?'hidden':'visible';},
        {rootMargin:'-56px 0px 0px 0px'}).observe(hero);
    }
  }
  const api = {safeURL,dateLabel,filterMembers,scoreState,scoreDistribution,validateDetail,renderSummary,renderRegulation,
    renderStatement,renderTopics,historySeries,renderHistory,renderDistribution,mount};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else {
    global.FederalAnalysis = api;
    const button = document.getElementById('fa-theme');
    let theme;
    try { theme=localStorage.getItem('theme'); } catch (_) { /* Storage is optional. */ }
    document.documentElement.dataset.theme=theme === 'dark' ? 'dark' : 'light';
    const setTheme = () => {
      const dark=document.documentElement.dataset.theme==='dark';
      if (button) { button.textContent=dark ? 'Light theme' : 'Dark theme'; button.setAttribute('aria-label',dark ? 'Switch to light theme' : 'Switch to dark theme'); }
    };
    setTheme();
    if (button) button.onclick=()=>{ const theme=document.documentElement.dataset.theme==='dark' ? 'light' : 'dark'; document.documentElement.dataset.theme=theme; try {localStorage.setItem('theme',theme);} catch (_) {} setTheme(); };
    mount(document.getElementById('federal-analysis'));
  }
})(typeof window !== 'undefined' ? window : globalThis);
