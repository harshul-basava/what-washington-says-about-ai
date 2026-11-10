/* Federal analysis. The index defines eligibility; each detail file owns its sources. */
(function (global) {
  'use strict';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = value => Number.isInteger(value) ? String(value) : String(Math.round(value * 100) / 100);
  const STANCES = {'-2':'Explicit opposition','-1':'Implied opposition','0':'No stated position','1':'Implied support','2':'Explicit support'};
  const LEVELS = {
    ai_overall:['Sees AI mainly as a threat','Sees more harm than good','Weighs harm and good equally','Sees AI mainly as an opportunity','Enthusiastic about AI'],
    agi_pilled:['Dismisses AGI','Sees AI as ordinary technology','Expects very large change','Thinks AGI is possible','Thinks AGI is near'],
    x_risk:['Dismisses AI x-risk','Mentions x-risk, plays it down','Calls x-risk a real risk','Wants action on x-risk','Calls x-risk a top priority'],
    china_race:['Rejects the China race','Mentions the China race','China race is one reason','China race is the main reason','China race outweighs all else'],
    regulation:['Opposes AI rules','Wants light-touch rules','Wants targeted rules','Wants substantial rules','Wants comprehensive rules']
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
  function renderRosterCoverage(coverage, organization='all') {
    if (coverage?.status !== 'available') return '<p class="fa-empty">Coverage inventory is unavailable.</p>';
    const all=coverage.organizations || [], selected=new Set([organization]);
    let changed=true;
    while (changed) { changed=false; for (const row of all) {
      if (selected.has(row.parent_id) && !selected.has(row.id)) { selected.add(row.id); changed=true; }
    } }
    const rows=all.filter(row=>organization==='all' || selected.has(row.id) || row.registry_id===organization);
    const table=items=>`<div class="fa-table-scroll"><table><thead><tr><th scope="col">Agency or office</th><th scope="col">Unique officials</th><th scope="col">Unresolved roles</th><th scope="col">Vacant roles</th><th scope="col">Office review</th><th scope="col">Last role review</th></tr></thead><tbody>${items.map(row=>`<tr><th scope="row">${row.registry_id ? `<a href="?organization=${encodeURIComponent(row.registry_id)}#fa-roster-coverage">${esc(row.name)}</a>` : esc(row.name)}</th><td>${count(row.included_people)}</td><td>${count(row.unresolved_roles)}</td><td>${count(row.role_counts?.vacant)}</td><td>${row.discovery_complete ? 'Public offices reviewed' : 'Review incomplete'}${row.pending_role_reviews ? ' · role changes need review' : ''}${row.unavailable_sources ? ' · source unavailable' : ''}</td><td>${esc(row.checked_on || 'Unknown')}</td></tr>`).join('')}</tbody></table></div>`;
    const main=organization==='all' ? rows.filter(row=>!row.parent_id) : rows;
    const offices=organization==='all' ? rows.filter(row=>row.parent_id) : [];
    return `<p>These counts describe tracked current officials. One official can hold several roles. Agency totals include their offices and count each official once.</p><p>Office discovery, source evidence, and completed judgments are separate measures. An empty profile remains in the roster.</p>${main.length ? table(main) : '<p>No reviewed inventory for this selection.</p>'}${offices.length ? `<details><summary>Component offices (${offices.length})</summary>${table(offices)}</details>` : ''}`;
  }
  function renderRoles(member) {
    const scope=member.government_scope || {}, source=safeURL(scope.source_url);
    return `<section class="fa-role-details"><h4>Government roles</h4>${scope.checked_on ? `<p>Current service checked ${esc(dateLabel(scope.checked_on))}${source ? ` · <a href="${esc(source)}" target="_blank" rel="noopener noreferrer">Role source</a>` : ''}</p>` : ''}${(member.roles || []).map(role=>{
      const url=safeURL(role.source_url), dates=[role.start_date,role.end_date].filter(Boolean).map(dateLabel).join(' to ');
      return `<p>${esc(role.title)}${dates ? ` · ${esc(dates)}` : ''}${role.end_date || role.status === 'historical' ? ' · historical role' : ''}${url ? ` · <a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Source</a>` : ''}</p>`;
    }).join('')}</section>`;
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
        reasons.every(reason=>['silent','no_statements'].includes(reason)) ? 'Not enough evidence: no statements on this question' : 'Score unavailable'};
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
  function renderStanceReview(review, statements) {
    if (review?.status!=='complete') return '';
    const accepted=review.accepted_sids || [];
    return `<section class="fa-profile-block fa-review"><h3>Astra review: AI overall</h3>
      <p><strong>${accepted.length ? 'Stance updated' : review.finding_count ? 'Finding below the confidence threshold' : 'No qualifying stance'}</strong> · ${count(review.n_statements)} statements reviewed · Source context checked for ${count(review.n_contexts)}.</p>
      <p>${esc(review.reason)}</p><p class="fa-note">Review confidence: ${esc(review.confidence)} of 5. This is the model's confidence, not a measured accuracy rate.</p>
      ${accepted.length ? `<p class="fa-citations">Corrected sources: ${citations(accepted,statements)}</p>` : ''}
      <p class="fa-models">${esc(review.model)} · ${esc(dateLabel(review.assessed_at?.slice(0,10)))}</p></section>`;
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
    const review=analysis.stance_review, contextURL=safeURL(review?.source_context?.url);
    const reviewLabel=review?.accepted ? `AI overall: ${fmt(review.labels.ai_overall)} · ${LEVELS.ai_overall[review.labels.ai_overall]}` :
      review?.decision==='uncertain' || score(review?.labels?.ai_overall) ? 'Finding below the confidence threshold' : 'No qualifying stance';
    const reviewHTML=review ? `<div class="fa-review"><h4>Astra stance review</h4><p><strong>${esc(reviewLabel)}</strong> · Confidence: ${esc(review.confidence?.ai_overall ?? review.review_confidence)} of 5.</p>
      <p>${esc(review.reason)}</p>${review.supporting_quote ? `<p class="fa-note">${review.support_basis==='context' ? 'Support from the original source context' : 'Support from the original excerpt'}:</p><blockquote>${esc(review.supporting_quote)}</blockquote>` : ''}
      ${contextURL ? `<p><a href="${esc(contextURL)}" target="_blank" rel="noopener noreferrer">Read the source context ↗</a></p>` : ''}
      ${review.accepted ? '<p class="fa-note">Astra supplies both AI overall columns for this correction. They are not independent judgments. The original assessments remain in the profile download.</p>' : ''}
      <p class="fa-models">${esc(review.model)} · ${esc(dateLabel(review.assessed_at?.slice(0,10)))}</p></div>` : '';
    return `<article class="fa-quote" id="${esc(quoteID(statement.sid))}" tabindex="-1"><div class="fa-quote-meta"><span class="fa-source-id">${esc(statement.sid)}</span>
      <span>${esc(dateLabel(statement.date))} · ${esc(statement.source_type || 'Source type unknown')}</span>
      ${source ? `<a href="${esc(source)}" target="_blank" rel="noopener noreferrer">Read source <span aria-hidden="true">↗</span></a>` : '<span class="fa-muted">Source link unavailable</span>'}</div>
      ${attribution ? `<p class="fa-attribution"><strong>${esc({personal:'Personal statement',official_role:'Official role',institutional:'Institutional statement'}[attribution.kind] || 'Attribution')}:</strong> ${esc(attribution.speaker || '')}${attribution.role ? ' · ' + esc(attribution.role) : ''}${attribution.note ? '. ' + esc(attribution.note) : ''}</p>` : '<p class="fa-attribution">Attribution context unavailable.</p>'}
      <blockquote>${esc(statement.text)}</blockquote><p class="fa-quote-topics">${(analysis.topics || []).map(t => `<span>${esc(t)}</span>`).join('')}</p>
      <details class="fa-assessment"><summary>${complete ? 'Assessment details' : 'Assessment pending'}</summary>
      <p class="fa-note">The two label columns feed the score formula. Confidence uses a model scale from 1 to 5; it does not measure accuracy.</p>
      ${reviewHTML}
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
    return `
      
      ${['reconstructed','observed'].map(kind => {
        const rows = historySeries(history,dimension,kind), label = kind === 'reconstructed' ? 'Reconstructed history' : 'Observed snapshots';
        return `<section class="fa-history-kind"><h4>${label}</h4>
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
    return `
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
      root.innerHTML = '<div class="fa-empty" role="status"><h2>Federal analysis is unavailable</h2><p>The export is missing or incomplete. Please reload the page later.</p><a href="policies.html#policy-section">Open the policy explorer</a></div>';
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
      organization:(data.organizations || []).some(o=>o.id===params.get('organization')) ? params.get('organization') : 'all',search:'',selected:initial?.id || null,dimension:data.dimensions[0]?.id,page:0,
      chartDimension:'x_risk',trange:'12m',topicrange:'12m',compare:'regulation',historyKind:'reconstructed',topic:data.topics[0],range:'12m',preset:'agi_low_risk',rule:null};
    let request = 0, currentDetail = null;
    const cache = new Map();
    const dimensionOptions=id=>data.dimensions.map(d=>`<option value="${esc(d.id)}" ${d.id===id?'selected':''}>${esc(d.title)}</option>`).join('');
    // the topic charts follow the question, as on the Congress page
    const TOPIC_OF={ai_overall:'jobs/economy',agi_pilled:'AGI/transformative',x_risk:'x-risk/loss of control',china_race:'China/competition',regulation:'regulation'};
    const TOPIC_NAME={'jobs/economy':'jobs and the economy','AGI/transformative':'AGI and transformative AI','x-risk/loss of control':'x-risk and loss of control','China/competition':'China and competition','regulation':'AI rules'};
    const HIGH={ai_overall:'are optimistic about AI',agi_pilled:'expect AGI',x_risk:'want action on AI x-risk',china_race:'say the China race drives their AI views',regulation:'want substantial AI rules'};
    const who=()=>state.scope==='institutions'?'Institutions':'Officials';
    root.innerHTML = `<section class="fc-controlbar" aria-label="Chart settings"><label>Question <select id="fc-dimension">${dimensionOptions(state.chartDimension)}</select></label><div class="fa-scope" role="group" aria-label="Profile type"><button type="button" data-scope="officials" aria-pressed="true">Executive officials</button><button type="button" data-scope="institutions" aria-pressed="false">Institutions</button></div></section>
<nav class="fc-toc" aria-label="Contents"><a href="#fc-cohort">Profiles by score</a><a href="#fc-agency-section">Scores by agency</a><a href="#fc-timeline-section">Scores over time</a><a href="#fc-recent-section">Recent changes</a><a href="#fc-topic-section">Topics</a><a href="#fc-members-section">All profiles</a></nav>
<section class="fc-section" id="fa-roster-coverage"><details><summary>Officials and offices covered</summary><label class="fc-control">Agency or office<select id="fa-agency"><option value="all">All organizations</option>${(data.organizations || []).map(o=>`<option value="${esc(o.id)}" ${o.id===state.organization ? 'selected' : ''}>${esc(o.name)}</option>`).join('')}</select></label><div id="fa-roster-table"></div></details></section>
      <section class="fc-section" id="fc-cohort"><h2 id="fc-cohort-title"></h2><p class="fc-description">Each dot is one profile, colored by the selected score.</p><div id="fc-dots"></div></section>
      <section class="fc-section" id="fc-agency-section"><h2>Scores by agency</h2><p class="fc-description">Profiles in each agency, by the selected score.</p><div id="fc-agencies"></div><div id="fc-agency-selection" aria-live="polite"></div></section>
      <section class="fc-section" id="fc-timeline-section"><h2 id="fc-timeline-title"></h2><p class="fc-description">Percent of profiles, month by month.</p><div class="fa-range" role="radiogroup" aria-label="Time range"><button type="button" role="radio" data-trange="3m" aria-checked="false">3 months</button><button type="button" role="radio" data-trange="12m" aria-checked="true">12 months</button><button type="button" role="radio" data-trange="all" aria-checked="false">All</button></div><div id="fc-timeline" class="fc-plot"></div></section>
      <section class="fc-section" id="fc-recent-section"><h2>Recent changes</h2><p class="fc-description">Scores that moved by more than 1 point in the last 60 days.</p><div id="fc-recent"></div></section>
      <section class="fc-section" id="fc-topic-section"><h2>Topics</h2><h3>Share of statements about each topic</h3><div class="fa-range" role="radiogroup" aria-label="Time range"><button type="button" role="radio" data-topicrange="3m" aria-checked="false">3 months</button><button type="button" role="radio" data-topicrange="12m" aria-checked="true">12 months</button><button type="button" role="radio" data-topicrange="all" aria-checked="false">All</button></div><div id="fc-topic-share"></div><h3 id="fc-voices-title"></h3><div id="fc-voices"></div></section>
      <section class="fc-section" id="fc-members-section"><h2>All profiles</h2><div class="fa-listbar"><input id="fa-search" type="search" placeholder="Search name or agency…" autocomplete="off" aria-label="Search profiles"></div><div id="fc-members"></div></section>`;
    const get = id => root.querySelector('#' + id);
    const selectedMembers=()=>filterMembers(data.members,{...state,search:''},data.organizations || []).sort((a,b)=>a.name.localeCompare(b.name));
    const levelText=(id,v)=>v===null||v===undefined?'Not enough evidence':Number.isInteger(v)?(LEVELS[id]||[])[v]:`Between “${LEVELS[id][Math.floor(v)]}” and “${LEVELS[id][Math.floor(v)+1]}”`;
    function renderCharts() {
      const members=selectedMembers(),dim=data.dimensions.find(d=>d.id===state.chartDimension),profiles=chartData?.profiles,topic=TOPIC_OF[state.chartDimension];
      get('fc-cohort-title').textContent=`${who()} by ${dim.title} score`;
      get('fc-dots').innerHTML=charts.renderDots(members,state.chartDimension);
      get('fc-agencies').innerHTML=charts.renderAgencies(members,state.chartDimension,data.organizations || []);
      get('fc-agency-selection').innerHTML='';
      const unavailable=`<p class="fa-empty" role="status">${esc(chartError)}</p>`;
      get('fc-timeline-title').textContent=`${who()} who ${HIGH[state.chartDimension]}, over time`;
      if (profiles) drawTimeline(members,profiles); else get('fc-timeline').innerHTML=unavailable;
      get('fc-recent').innerHTML=profiles?charts.renderRecent(members,profiles,state.chartDimension,data.built_on.slice(0,10)):unavailable;
      get('fc-topic-share').innerHTML=profiles?charts.renderTopicShare(members,profiles,data.topics,state.topicrange,data.built_on.slice(0,10)):unavailable;
      get('fc-voices-title').textContent=`${who()} who talk most about ${TOPIC_NAME[topic]}`;
      get('fc-voices').innerHTML=charts.renderVoices(members,topic);
      renderTable();
    }
    // same look as the Congress page's chart over time: one line, percent axis, end label, hover readout
    function drawTimeline(members,profiles) {
      const el=get('fc-timeline'); el.innerHTML='';
      const Plot=global.Plot, css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
      const end=new Date(data.built_on.slice(0,10)+'T00:00:00Z'), days={'3m':90,'12m':365}[state.trange];
      const rows=charts.cohortHistory(members,profiles,state.chartDimension,'reconstructed').map(r=>({d:new Date(r.date+'T00:00:00Z'),v:r.percent/100,high:r.high,n:r.total}))
        .filter(r=>!days || r.d>=new Date(+end-days*864e5));
      if (!Plot || !rows.length) { el.innerHTML='<p class="fa-empty">No history in this range.</p>'; return; }
      const W=Math.max(300,el.clientWidth-24), name=who();
      el.append(Plot.plot({width:W,height:290,marginLeft:48,marginRight:90,marginTop:20,style:{background:'transparent',fontSize:'11px',color:css('--fg')},
        x:{type:'utc',label:null}, y:{label:null,percent:true,grid:true,tickFormat:d=>d+'%',domain:[0,Math.max(10,...rows.map(r=>r.v*100))]},
        marks:[Plot.ruleY([0],{stroke:css('--line')}),
          Plot.line(rows,{x:'d',y:'v',stroke:css('--accent'),strokeWidth:2}),
          Plot.text(rows.slice(-1),{x:'d',y:'v',text:()=>name,fill:css('--accent'),dx:6,textAnchor:'start',fontWeight:600}),
          Plot.tip(rows,Plot.pointerX({x:'d',y:'v',fill:css('--raised')||css('--bg'),stroke:css('--line'),
            channels:{Date:r=>r.d.toISOString().slice(0,10),Share:r=>`${(r.v*100).toFixed(0)}%`,Profiles:r=>`${r.high} of ${r.n}`},format:{x:false,y:false}}))]}));
    }
    function renderTable() {
      const q=state.search.trim().toLowerCase();
      const rows=selectedMembers().filter(m=>!q || [m.name,m.organization_name,...(m.aliases||[]),...(m.roles||[]).map(r=>r.title)].join(' ').toLowerCase().includes(q));
      get('fc-members').innerHTML=rows.length?charts.renderMembers(rows,data.dimensions):'<p class="fa-empty">No profile matches this search.</p>';
      const tr=[...get('fc-members').querySelectorAll('tr')].find(r=>r.querySelector(`[data-profile="${CSS.escape(state.selected||'')}"]`));
      if (tr) { tr.classList.add('fa-selected'); tr.insertAdjacentHTML('afterend',`<tr class="fa-detail"><td colspan="${tr.children.length}"><div id="fa-profile-panel" class="fa-profile-panel" aria-live="polite"></div></td></tr>`); }
      if (tr && currentDetail?.id===state.selected) { const m=data.members.find(x=>x.id===state.selected); if (m) renderProfile(m,currentDetail); }
    }
    const panel=()=>get('fa-profile-panel') || {set innerHTML(_){}, scrollIntoView(){}};
    function updateURL() {
      if (!global.history?.replaceState) return;
      const url = new URL(global.location.href);
      url.searchParams.set('scope',state.scope);
      if (state.organization !== 'all') url.searchParams.set('organization',state.organization); else url.searchParams.delete('organization');
      if (state.selected) url.searchParams.set('profile',state.selected); else url.searchParams.delete('profile');
      url.hash = '';
      global.history.replaceState(null,'',url);
    }
    // one quote, styled like the quotes on the Congress page
    function quoteHTML(st) {
      const src=safeURL(st.url), topics=(st.analysis?.topics||[]);
      return `<div class="fa-q" id="${esc(quoteID(st.sid))}" tabindex="-1">“${esc(st.text)}”<div class="fa-q-src">${esc(dateLabel(st.date))}${src?` · <a href="${esc(src)}" target="_blank" rel="noopener noreferrer">source</a>`:''} ${topics.map(t=>`<span class="fa-chip">${esc(t)}</span>`).join('')}</div></div>`;
    }
    function renderSources() {
      if (!currentDetail) return;
      const sources = currentDetail.statements, pages = Math.max(1,Math.ceil(sources.length/20));
      state.page = Math.min(state.page,pages-1);
      get('fa-sources').innerHTML = sources.length ? sources.slice(state.page*20,(state.page+1)*20).map(quoteHTML).join('') : '<p class="fa-empty">No verified statements in this profile.</p>';
      get('fa-source-pages').innerHTML = sources.length > 20 ? `<button type="button" data-source-page="${state.page-1}" ${state.page===0 ? 'disabled' : ''}>Previous</button><span>Page ${state.page+1} of ${pages}</span><button type="button" data-source-page="${state.page+1}" ${state.page===pages-1 ? 'disabled' : ''}>Next</button>` : '';
    }
    function rulesHTML(member) {
      const areas=member.regulation?.areas||{}, name=id=>data.regulation_areas.find(a=>a.id===id)?.title||id;
      const part=sgn=>Object.entries(areas).filter(([,v])=>Math.sign(v?.stance||0)===sgn).map(([id,v])=>`<span class="fa-chip" title="${esc((Math.abs(v.stance)===2?'Explicit. ':'Implied. ')+(v.why||''))}">${esc(name(id))}</span>`).join('');
      const sup=part(1), opp=part(-1);
      return sup||opp ? `<p class="fa-muted fa-rules">${sup?`Policies they support: ${sup}`:''}${sup&&opp?'<br>':''}${opp?`Policies they oppose: ${opp}`:''}</p>` : '';
    }
    function renderProfile(member, detail) {
      panel().innerHTML = `<h3 id="fa-profile-name" tabindex="-1">${esc(member.name)}</h3>
        <p class="fa-muted fa-profile-meta">${esc(member.organization_name || '')}${member.entity_type === 'institution' ? ' · Institution' : ''} · ${count(member.n_statements)} verified statement${count(member.n_statements)===1?'':'s'}</p>
        ${member.summary?.status==='complete' && member.summary.text ? renderSummary(member.summary,detail.statements) : ''}
        ${rulesHTML(member)}
        ${member.entity_type === 'person' ? `<details><summary>Government roles and sources</summary>${renderRoles(member)}</details>` : ''}
        ${renderStanceReview(member.stance_review,detail.statements)}
        <div class="fa-dims">${data.dimensions.map(d=>{const v=scoreState(member,d.id).value;return `<div class="fa-dim"><b>${esc(d.title)}</b>${esc(levelText(d.id,v))}</div>`;}).join('')}</div>
        <div id="fa-sources"></div><div id="fa-source-pages" class="fa-pages"></div>`;
      renderSources();
    }
    async function loadProfile(member) {
      const token = ++request;
      currentDetail = null;
      panel().innerHTML = '<p class="fa-empty" role="status">Loading…</p>';
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
        panel().innerHTML = `<p class="fa-empty" role="status">${esc(error.message)} <button type="button" data-retry>Retry</button></p>`;
      }
    }
    function select(id, scroll) {
      if (scroll && state.selected===id && get('fa-profile-panel')) { state.selected=null; updateURL(); renderTable(); return; }   // click again to close
      state.selected=id; state.page=0; updateURL(); renderTable();
      const member=data.members.find(m=>m.id===id); if (!member) { panel().innerHTML=''; return; }
      loadProfile(member);
    }
    function showProfile(id, smooth=true) {
      const m=data.members.find(x=>x.id===id); if (!m) return;
      state.search=m.name; get('fa-search').value=m.name; state.selected=null; select(id,false);
      get('fc-members-section').scrollIntoView({block:'start',behavior:smooth?'smooth':'instant'});
    }
    function render() {
      get('fa-roster-table').innerHTML=renderRosterCoverage(data.roster_coverage,state.organization);
      root.querySelectorAll('[data-scope]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.scope===state.scope)));
      renderCharts();
      if (state.selected && selectedMembers().some(m=>m.id===state.selected)) select(state.selected,false);
      else { state.selected=null; request++; currentDetail=null; panel().innerHTML=''; updateURL(); }
    }
    // keep the reader's place when a setting redraws the charts
    function keepPlace(fn) {
      const hs=[...root.querySelectorAll('h2[id], h3[id], section[id]')];
      const anchor=hs.filter(h=>h.getBoundingClientRect().top<=innerHeight*0.4).pop(), before=anchor&&anchor.getBoundingClientRect().top;
      fn();
      if (anchor) { const d=anchor.getBoundingClientRect().top-before; if (Math.abs(d)>1) global.scrollBy({top:d,behavior:'instant'}); }
    }
    get('fa-agency').addEventListener('change',event=>{ state.organization=event.target.value; render(); });
    get('fa-search').addEventListener('input',event=>{ state.search=event.target.value; renderTable(); });
    root.addEventListener('change',event=>{
      if (event.target.id==='fc-dimension') { state.chartDimension=event.target.value; keepPlace(renderCharts); }
    });
    root.addEventListener('click',event=>{
      const tr=event.target.closest('[data-trange]'), tp=event.target.closest('[data-topicrange]');
      if (tr || tp) { const key=tr?'trange':'topicrange', b=tr||tp; state[key]=b.dataset[key];
        b.parentElement.querySelectorAll('button').forEach(x=>x.setAttribute('aria-checked',String(x===b)));
        const members=selectedMembers(), profiles=chartData?.profiles; if (!profiles) return;
        keepPlace(()=>{ if (tr) drawTimeline(members,profiles); else get('fc-topic-share').innerHTML=charts.renderTopicShare(members,profiles,data.topics,state.topicrange,data.built_on.slice(0,10)); });
        return; }
      const scope = event.target.closest('[data-scope]');
      if (scope) { state.scope=scope.dataset.scope; state.selected=null; state.rule=null; keepPlace(render); return; }
      const profile = event.target.closest('[data-profile]');
      if (profile) { event.preventDefault(); if (profile.closest('#fc-members')) select(profile.dataset.profile,true); else showProfile(profile.dataset.profile); return; }
      const agency=event.target.closest('[data-agency-group]');
      if(agency) {
        const group=charts.agencyDistribution(selectedMembers(),state.chartDimension,data.organizations || []).find(g=>g.id===agency.dataset.agencyGroup);
        get('fc-agency-selection').innerHTML=`<h3>${esc(group.name)}</h3><div class="fc-profile-chips">${group.members.map(m=>`<a href="#fc-members-section" data-profile="${esc(m.id)}">${esc(m.name)}</a>`).join('')}</div>`;
        return;
      }
      const retry = event.target.closest('[data-retry]');
      if (retry) { const member=data.members.find(m=>m.id===state.selected); if (member) loadProfile(member); return; }
      const page = event.target.closest('[data-source-page]');
      if (page && currentDetail) { state.page=Math.max(0,Number(page.dataset.sourcePage)); renderSources(); get('fa-sources').scrollIntoView({block:'start'}); return; }
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
    // mark the section in view, as on the other pages
    const tocLinks=[...root.querySelectorAll('.fc-toc a[href^="#"]')];
    const tocActive=()=>{ let cur=null; for (const a of tocLinks){ const el=document.getElementById(a.getAttribute('href').slice(1)); if (el && el.getBoundingClientRect().top<170) cur=a; } tocLinks.forEach(a=>a.classList.toggle('active',a===cur)); };
    global.addEventListener('scroll',()=>global.requestAnimationFrame(tocActive),{passive:true}); tocActive();
    if (hero && toc && 'IntersectionObserver' in global) new IntersectionObserver(entries=>{toc.style.visibility=entries[0].isIntersecting?'hidden':'visible';},{rootMargin:'-56px 0px 0px 0px'}).observe(hero);
    if (initial) global.requestAnimationFrame(()=>showProfile(initial.id,false));
  }
  const api = {renderRosterCoverage,renderRoles,safeURL,dateLabel,filterMembers,scoreState,scoreDistribution,validateDetail,renderSummary,renderStanceReview,renderRegulation,
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
