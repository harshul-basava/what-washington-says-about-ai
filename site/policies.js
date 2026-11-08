/* Policy explorer; independent of the legacy charts and their external libraries. */
(function (global) {
  'use strict';
  const LABELS = {support:'Support', oppose:'Oppose', mixed:'Mixed positions', neutral:'Description only',
    unclear:'Unclear', disputed:'Models disagree', pending:'Assessment pending', review_required:'Human review required', not_relevant:'Not relevant'};
  const COVERAGE = {pending:'Assessment pending', partial:'Partial assessment',
    no_matching_evidence:'No matching evidence', no_relevant_evidence:'No relevant evidence'};
  const FACETS = {competition_priority:'Competition as a priority', speed_over_safety:'Speed over safeguards',
    safety_over_speed:'Safeguards despite competition', cooperation:'Cooperation', race_skepticism:'Race skepticism',
    export_restrictions:'Restrict exports', export_access:'Expand export access', tighten_controls:'Tighten controls',
    ease_controls:'Ease controls', enforcement:'Enforce controls', allied_coordination:'Coordinate with allies',
    cloud_access:'Cloud access', chip_tracking:'Chip tracking', ongoing_access:'Ongoing internal access',
    independence:'Auditor independence', government_assignment:'Government assigns auditors', mandatory:'Mandatory oversight', voluntary:'Voluntary oversight'};
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  function safeURL(value) {
    try { const u = new URL(value); return ['http:','https:'].includes(u.protocol) ? esc(u.href) : '#'; }
    catch (_) { return '#'; }
  }
  function party(value) {
    return /^dem|^dfl$|^D$/i.test(value) ? 'D' : /^rep|^R$/i.test(value) ? 'R' : /^ind|^I$/i.test(value) ? 'I' : '';
  }
  function dateLabel(value) {
    return !value ? 'Date unknown' : value + (/^\d{4}$/.test(value) ? ' (year only)' : /^\d{4}-\d{2}$/.test(value) ? ' (day unknown)' : '');
  }
  function evidenceRecords(payload, member, target) {
    const records = payload?.policies?.[target] || (member.policies[target].candidates === 0 ? [] : undefined);
    if (payload?.id !== member.id || !Array.isArray(records) || records.length !== member.policies[target].candidates) {
      throw new Error('Missing or stale source quotes');
    }
    return records;
  }
  function summaryLabel(result) {
    if (!result) return 'Assessment pending';
    const text = result.stance ? LABELS[result.stance] : COVERAGE[result.coverage] || 'No relevant evidence';
    return text + (result.human_review ? ` · ${result.human_review} need human review` : '') + (result.facet_disagreements && result.stance !== 'disputed' ? ' · details disputed' : '') +
      (result.stance && result.coverage === 'partial' ? ' · partial assessment' : '');
  }
  function filterMembers(members, state) {
    const search = (state.search || '').trim().toLowerCase();
    return members.filter(m => {
      const scope = m.entity_type === 'institution' ? 'institutions' : m.branch === 'executive' ? 'executive' : 'congress';
      if (state.scope && state.scope !== scope) return false;
      if (state.organization && state.organization !== 'all' && !(m.organization_ids || [m.organization_id]).includes(state.organization)) return false;
      const r = m.policies[state.policy] || {};
      const stanceOK = !state.stance || state.stance === 'all' ||
        (state.stance === 'no_evidence' ? ['no_matching_evidence','no_relevant_evidence'].includes(r.coverage) :
          state.stance === 'pending' ? ['pending','partial'].includes(r.coverage) : r.stance === state.stance);
      const searchable = [m.name, m.state, m.organization_name, ...(m.aliases || []), ...(m.roles || []).map(r=>r.title)].join(' ').toLowerCase();
      return stanceOK && (!search || searchable.includes(search)) &&
        (!state.party || state.party === 'all' || party(m.party) === state.party) &&
        (!state.population || state.population === 'all' || m.status === state.population);
    });
  }
  const judgeName = judge => ({sonnet:'Claude',gpt:'GPT',deepseek:'DeepSeek V4.1 Flash 1017',astra:'Astra'}[judge] || judge);
  function renderProfile(member, organizations, members) {
    if (member.branch !== 'executive') return '';
    const orgName = id => organizations.find(o=>o.id===id)?.name || id;
    const link = (id, title) => members.some(m=>m.id===id) ? `<button type="button" class="policy-profile-link" data-open-subject="${esc(id)}">${esc(title)}</button>` : esc(title);
    const roles = (member.roles || []).map(r=>`<li>${esc(r.title)} · ${link(r.organization_id, orgName(r.organization_id))}<br>
      <span class="note">${r.start_date ? esc(r.start_date) : 'Start date unknown'}${r.end_date ? ' to ' + esc(r.end_date) : '; no end date recorded'} · Source checked ${esc(r.verified_on)} · <a href="${safeURL(r.source_url)}" target="_blank" rel="noopener noreferrer">Role source</a>${r.source_type === 'reporting' ? ' (reported membership)' : ''}</span></li>`).join('');
    const linked = member.entity_type === 'institution' ? members.filter(m=>m.entity_type==='person' && (m.roles || []).some(r=>r.organization_id===member.id)) : [];
    return `<div class="policy-profile"><p>${esc(member.description || (member.entity_type === 'institution' ? 'Institutional statements do not establish the personal views of its officials.' : 'Each quote identifies the role in which this official spoke.'))}</p>
      ${member.source_url ? `<p class="note"><a href="${safeURL(member.source_url)}" target="_blank" rel="noopener noreferrer">Profile source</a>${member.verified_on ? ' · Profile checked ' + esc(member.verified_on) : ''}</p>` : ''}
      ${roles ? `<h4>Roles and memberships</h4><ul>${roles}</ul>` : ''}
      ${linked.length ? `<p>Officials in this dataset: ${linked.map(m=>link(m.id,m.name)).join(', ')}.</p>` : ''}</div>`;
  }
  function renderRecord(record) {
    const a = record.attribution;
    const attribution = a ? `<p class="note policy-attribution"><b>${esc({personal:'Personal statement',official_role:'Official role',institutional:'Institutional statement'}[a.kind])}:</b> ${esc(a.speaker)}${a.role ? ' · ' + esc(a.role) : ''}. ${esc(a.note || '')}</p>` : '';
    const judges = Object.entries(record.judges || {}).map(([judge, result]) =>
      `<div class="policy-judge"><b>${esc(judgeName(judge))}: ${esc(LABELS[result.stance])}.</b> ${esc(result.reason)}
      ${Number.isFinite(result.confidence) ? `<p class="note">Self-reported confidence: ${esc(result.confidence)}. ${esc(result.confidence_reason || '')}</p>` : ''}
      <div>${(result.facets || []).map(f => `<span class="chip">${esc(FACETS[f] || f)}</span>`).join('')}</div></div>`).join('');
    const route = record.strategy === 'confidence_cascade' ? `<p class="note">${record.final_judge ? `Final assessment: ${esc(judgeName(record.final_judge))}.` : esc(LABELS[record.stance]) + '.'} ${esc(record.review_reason || '')}${record.model_disagreement ? ' The models gave different stances; both appear below.' : ''}</p>` : '';
    return `<article class="policy-quote"><p class="note">${esc(dateLabel(record.date))} · ${esc(record.source_type)} ·
      <a href="${safeURL(record.url)}" target="_blank" rel="noopener noreferrer">Read source</a> · ${record.library_only ? 'No policy assessment' : esc(LABELS[record.stance])}</p>
      ${attribution}<blockquote>${esc(record.text)}</blockquote>${route}${record.facet_disagreement ? '<p class="note">Models disagree on the details. Read each judgment below.</p>' : ''}${judges || (record.library_only ? '<p class="note">No assessment for the selected policy.</p>' : '<p>Assessment pending.</p>')}</article>`;
  }
  async function mount(root) {
    if (!root) return;
    let data;
    try {
      const res = await fetch('data/policies.json');
      if (!res.ok) throw new Error('Policy data unavailable');
      data = await res.json();
    } catch (_) {
      root.innerHTML = '<p role="status">Policy judgments are unavailable. Please try again later.</p>';
      return;
    }
    const isCascade = data.strategy?.kind === 'confidence_cascade';
    const state = {policy:data.policies[0].id, scope:'congress', organization:'all', stance:'all', party:'all', population:'all', search:'', page:0};
    let chartData = null, chartError = false;
    const cache = new Map();
    const options = ['bill','framework','issue'].map(kind => `<optgroup label="${{bill:'Named bills',framework:'Policy frameworks',issue:'Policy questions'}[kind]}">
      ${data.policies.filter(p => p.kind === kind).map(p=>`<option value="${esc(p.id)}">${esc(p.title)}</option>`).join('')}</optgroup>`).join('');
    root.innerHTML = `${isCascade ? `<p class="note">DeepSeek V4.1 Flash 1017 assesses each statement. Astra independently reviews confidence below ${Number(data.strategy.threshold).toFixed(2)}. These confidence scores are model estimates; they are not calibrated accuracy measurements. Cases that remain uncertain require human review.</p>` : ''}<div class="policy-scope" role="group" aria-label="Policy coverage">
      <button type="button" data-scope="congress" aria-pressed="true">Congress</button>
      <button type="button" data-scope="executive" aria-pressed="false">Executive officials</button>
      <button type="button" data-scope="institutions" aria-pressed="false">Institutions</button>
    </div><p class="note" id="policy-scope-note"></p><div class="policy-controls">
      <label>Policy or question<select id="policy-choice">${options}</select></label>
      <label>Observed stance<select id="policy-stance"><option value="all">All stances</option>${['support','oppose','mixed','neutral','unclear','disputed','pending'].map(s=>`<option value="${s}">${LABELS[s]}</option>`).join('')}<option value="no_evidence">No evidence found</option></select></label>
      <label id="policy-party-control">Party<select id="policy-party"><option value="all">All parties</option><option value="D">Democrats</option><option value="R">Republicans</option><option value="I">Independents</option></select></label>
      <label id="policy-population-control">Members<select id="policy-population"><option value="all">Current and members-elect</option><option value="current">Current members</option><option value="member_elect">Members-elect</option></select></label>
      <label id="policy-organization-control" hidden>Agency or membership<select id="policy-organization"><option value="all">All organizations</option>${(data.organizations || []).map(o=>`<option value="${esc(o.id)}">${esc(o.name)}</option>`).join('')}</select></label>
      <label class="policy-search">Name, state, or organization<input type="search" id="policy-search" placeholder="Search profiles"></label>
    </div><div id="policy-chart-overview" class="pc-root"></div>
    <h3 id="policy-detail-title" tabindex="-1"></h3><p id="policy-description"></p><p class="note" id="policy-source"></p>
    <div id="policy-chart-detail" class="pc-root"></div><h3>Profiles and source quotes</h3>
    <div id="policy-counts" class="policy-counts" aria-live="polite"></div>
    <p class="note">These labels summarize the available statement history. They do not establish a current position.
    No matching evidence means that the search found no candidate quote in this dataset. It does not mean opposition.</p>
    <div id="policy-results"></div><div class="policy-pages"><button id="policy-prev">Previous</button><span id="policy-page" aria-live="polite"></span><button id="policy-next">Next</button></div>
    <p class="note"><a href="data/policies.csv" download>Download policy summaries (CSV)</a> ·
    <a href="data/policies.json" download>Download policy data (JSON)</a> · Export built ${esc(data.built_on)}</p>`;
    const get = id => root.querySelector('#' + id);
    function renderCharts() {
      if (!global.PolicyCharts) {
        get('policy-chart-overview').innerHTML = '<p role="status">Charts are unavailable. Reload the page to retry.</p>';
        return;
      }
      const members = filterMembers(data.members, {...state, stance:'all'});
      const target = data.policies.find(p=>p.id === state.policy);
      global.PolicyCharts.renderOverview(get('policy-chart-overview'), members, data.policies, state.policy, id=>{
        state.policy = id;
        state.stance = 'all';
        state.page = 0;
        get('policy-choice').value = id;
        get('policy-stance').value = 'all';
        render();
        get('policy-detail-title').focus({preventScroll:true});
        get('policy-detail-title').scrollIntoView({block:'start',behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
      });
      global.PolicyCharts.renderSelected(get('policy-chart-detail'), members, target, chartData, FACETS, chartError, state.scope);
    }
    async function expand(details, member, target) {
      if (!details.open || details.dataset.loaded) return;
      const panel = details.querySelector('.policy-evidence');
      panel.textContent = 'Loading source quotes…';
      try {
        if (!cache.has(member.id)) {
          const response = await fetch(`data/policy_members/${encodeURIComponent(member.id)}.json`);
          if (!response.ok) throw new Error('Missing source quotes');
          cache.set(member.id, await response.json());
        }
        const records = evidenceRecords(cache.get(member.id), member, target);
        const relevant = records.filter(r => r.stance !== 'not_relevant');
        const excluded = records.filter(r => r.stance === 'not_relevant');
        panel.innerHTML = relevant.map(renderRecord).join('') || (records.length ? '<p>The final assessments found no relevant position in these candidate quotes.</p>' : '<p>No matching evidence for this policy in the collected sources.</p>');
        const selectedIDs = new Set(records.map(r=>r.sid));
        const other = (cache.get(member.id).statements || []).filter(r=>!selectedIDs.has(r.sid));
        if (other.length) panel.innerHTML += `<details class="policy-excluded"><summary>${other.length} other collected statements</summary><p class="note">These sources did not match the selected policy. They do not establish a position on it.</p>${other.map(r=>renderRecord({...r,stance:'not_relevant',judges:{},library_only:true})).join('')}</details>`;
        if (records.some(r => !r.date || r.date.length < 10)) panel.insertAdjacentHTML('afterbegin', '<p class="note">Some dates are incomplete. Undated quotes appear first. Year-only and month-only quotes appear first within their possible period.</p>');
        if (excluded.length) panel.innerHTML += `<details class="policy-excluded"><summary>${excluded.length} candidate quotes excluded by the final assessment</summary>${excluded.map(renderRecord).join('')}</details>`;
        details.dataset.loaded = 'true';
      } catch (_) {
        cache.delete(member.id);
        panel.innerHTML = '<p role="alert">The source quotes did not load. Close and reopen this profile to retry.</p>';
      }
    }
    function render() {
      const target = data.policies.find(p => p.id === state.policy);
      const congress = state.scope === 'congress';
      get('policy-party-control').hidden = !congress;
      get('policy-population-control').hidden = !congress;
      get('policy-organization-control').hidden = congress;
      root.querySelectorAll('[data-scope]').forEach(b=>b.setAttribute('aria-pressed', String(b.dataset.scope===state.scope)));
      get('policy-scope-note').textContent = congress ? 'Congressional policy statements. The five-score charts above cover Congress only.' :
        `Curated federal coverage, checked ${data.subjects_verified_on || data.built_on}. ${state.scope === 'institutions' ? 'Each profile represents an institution. Statements do not establish its officials’ personal views.' : 'Each official counts once. Agency filters include linked roles; bars use each official’s primary organization.'} New federal sources require a manual refresh.`;
      get('policy-detail-title').textContent = target.title;
      renderCharts();
      get('policy-description').textContent = target.kind === 'issue' ?
        ({export_controls:'Positions on restrictions and enforcement for overseas access to AI chips, models, and compute.',
          embedded_ivos:'Positions on independent verification organizations (IVOs) with ongoing internal or on-site access to AI labs. General audit support alone does not qualify.',
          china_race_dynamics:'Support means that the speaker makes AI competition with China a policy priority. Additional labels identify safety, speed, cooperation, and export policy.'}[target.id] || target.title) :
        `Positions on ${target.title}. General views about AI do not establish support for this specific proposal.`;
      get('policy-source').innerHTML = `${esc(target.version)} · <a href="${safeURL(target.source_url)}" target="_blank" rel="noopener noreferrer">Policy reference</a>`;
      const rows = filterMembers(data.members, state).sort((a,b) =>
        (b.policies[state.policy].relevant - a.policies[state.policy].relevant) || a.name.localeCompare(b.name));
      const pages = Math.max(1, Math.ceil(rows.length / 30));
      state.page = Math.min(state.page, pages - 1);
      const page = rows.slice(state.page * 30, (state.page + 1) * 30);
      const assessed = rows.reduce((n,m)=>n+m.policies[state.policy].assessed,0);
      const candidates = rows.reduce((n,m)=>n+m.policies[state.policy].candidates,0);
      get('policy-counts').textContent = `${rows.length} profile${rows.length === 1 ? '' : 's'} in this view · ${assessed} of ${candidates} candidate statements with final assessments${isCascade ? ` · ${rows.reduce((n,m)=>n+(m.policies[state.policy].astra_reviewed || 0),0)} accepted after Astra review · ${rows.reduce((n,m)=>n+(m.policies[state.policy].human_review || 0),0)} need human review` : ''}`;
      get('policy-results').innerHTML = page.length ? page.map(m => {
        const r = m.policies[state.policy];
        const body = `<span><b>${esc(m.name)}</b><span class="policy-member-meta">${m.branch === 'executive' ? esc(m.organization_name) + (m.entity_type === 'institution' ? ' · Institution' : ' · Official') : party(m.party) + ' · ' + esc(m.state) + ' · ' + esc(m.chamber) + (m.status === 'member_elect' ? ' · member-elect' : '')}</span></span>
          <span class="policy-badge policy-${esc(r.stance || 'none')}">${esc(summaryLabel(r))}</span>
          <span class="policy-evidence-count">${r.relevant} relevant quote${r.relevant === 1 ? '' : 's'}${r.has_undated_evidence ? '<br>Includes undated quotes' : r.last_statement_date ? '<br>' + esc(dateLabel(r.last_statement_date)) : ''}</span>`;
        return r.candidates || m.branch === 'executive' ? `<details class="policy-member" data-person="${esc(m.id)}"><summary>${body}</summary>${renderProfile(m,data.organizations || [],data.members)}<div class="policy-evidence"></div></details>` : `<div class="policy-member policy-empty">${body}</div>`;
      }).join('') : '<p>No profiles match these filters.</p>';
      root.querySelectorAll('details.policy-member').forEach(details => {
        const member = data.members.find(m => m.id === details.dataset.person);
        const targetID = state.policy;
        details.addEventListener('toggle', () => expand(details, member, targetID));
      });
      get('policy-prev').disabled = state.page === 0;
      get('policy-next').disabled = state.page === pages - 1;
      get('policy-page').textContent = `Page ${state.page + 1} of ${pages}`;
    }
    for (const [id,key] of [['policy-choice','policy'],['policy-stance','stance'],['policy-party','party'],['policy-population','population'],['policy-search','search'],['policy-organization','organization']]) {
      get(id).addEventListener('input', e => { state[key] = e.target.value; state.page = 0; render(); });
    }
    function setScope(scope) {
      state.scope=scope; state.party='all'; state.population='all'; state.organization='all'; state.stance='all'; state.search=''; state.page=0;
      for (const id of ['policy-party','policy-population','policy-organization','policy-stance']) get(id).value='all';
      get('policy-search').value='';
    }
    root.querySelectorAll('[data-scope]').forEach(b=>b.onclick=()=>{setScope(b.dataset.scope); render();});
    root.addEventListener('click', e=>{
      const button=e.target.closest('[data-open-subject]');
      if (!button) return;
      const member=data.members.find(m=>m.id===button.dataset.openSubject);
      if (!member) return;
      setScope(member.entity_type==='institution' ? 'institutions' : 'executive');
      state.search=member.name; get('policy-search').value=member.name; render();
      const profile=Array.from(root.querySelectorAll('details.policy-member')).find(el=>el.dataset.person===member.id);
      if (profile) {profile.open=true; profile.scrollIntoView({block:'start'}); profile.querySelector('summary').focus({preventScroll:true});}
    });
    get('policy-prev').onclick = () => { state.page--; render(); };
    get('policy-next').onclick = () => { state.page++; render(); };
    render();
    fetch('data/policy_charts.json').then(res=>{
      if (!res.ok) throw new Error('Chart data unavailable');
      return res.json();
    }).then(result=>{
      if (result.revision !== data.chart_revision || !data.policies.every(p=>Array.isArray(result.policies?.[p.id]))) {
        throw new Error('Chart data does not match member summaries');
      }
      chartData = result;
      renderCharts();
    }).catch(()=>{ chartError = true; chartData = null; renderCharts(); });
    let chartWidth = get('policy-chart-detail').clientWidth;
    if (typeof ResizeObserver !== 'undefined') new ResizeObserver(()=>{
      const width = get('policy-chart-detail').clientWidth;
      if (width !== chartWidth) { chartWidth = width; renderCharts(); }
    }).observe(get('policy-chart-detail'));
  }
  const api = {filterMembers, renderRecord, renderProfile, summaryLabel, evidenceRecords, mount};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else { global.PolicyView = api; mount(document.getElementById('policy-explorer')); }
})(typeof window !== 'undefined' ? window : globalThis);
