const test = require('node:test');
const assert = require('node:assert/strict');
const view = require('../site/federal-analysis.js');

test('roster coverage distinguishes unknown scope and escapes office names', () => {
  assert.match(view.renderRosterCoverage(null), /Coverage inventory is unavailable/);
  const coverage={status:'available',checked_on:'2026-11-10',summary:{},organizations:[
    {id:'agency',registry_id:'agency',name:'Agency <script>',parent_id:null,included_people:2,
     included_roles:3,role_counts:{vacant:1},unresolved_roles:1,discovery_complete:false,checked_on:'2026-11-10'},
    {id:'office',registry_id:'office',name:'Office',parent_id:'agency',included_people:1,
     included_roles:1,role_counts:{},unresolved_roles:0,discovery_complete:true,checked_on:'2026-11-10'}]};
  const html=view.renderRosterCoverage(coverage);
  assert.match(html,/Agency &lt;script&gt;/);
  assert.doesNotMatch(html,/<script>/);
  assert.match(html,/Review incomplete/);
  assert.match(html,/Office/);
  assert.match(html,/Unique officials/);
  assert.match(view.renderRosterCoverage(coverage,'office'), /Public offices reviewed/);
  assert.doesNotMatch(view.renderRosterCoverage(coverage,'office'), /Agency &lt;script&gt;/);
});

test('role facts show verification sources without unsafe links or invented dates', () => {
  const html=view.renderRoles({government_scope:{checked_on:'2026-11-10',source_url:'https://example.gov/current'},
    roles:[{title:'Acting Director',organization_id:'agency',source_url:'javascript:alert(1)',start_date:null,end_date:null}]});
  assert.match(html,/Acting Director/);
  assert.match(html,/Current service checked/);
  assert.doesNotMatch(html,/javascript:|Date unknown/);
  const historical=view.renderRoles({roles:[{title:'Former adviser',status:'historical',end_date:null}]});
  assert.match(historical,/historical role/);
});

const dimensions = [{id:'ai_overall',title:'AI overall'}, {id:'x_risk',title:'Catastrophic risk'}];
const member = (overrides = {}) => ({id:'official', name:'An Official', entity_type:'person',
  organization_id:'child',organization_ids:['child','task'],organization_name:'Child agency',
  n_statements:4,n_labeled:4,status:'complete',scores:{ai_overall:2,x_risk:0},
  score_details:{x_risk:{reason_a:'silent',reason_b:'silent'}},summary:{status:'complete',text:'A cited summary.',sids:['s1']},
  topics:{safety:2},regulation:{status:'complete',areas:{}},...overrides});
const organizations = [{id:'parent',name:'Department'}, {id:'child',name:'Child agency',parent_id:'parent'},
  {id:'task',name:'Task force'}];

test('agency and name filters preserve separate unique officials and institutions', () => {
  const official=member();
  const institution=member({id:'agency',name:'The Agency',entity_type:'institution'});
  const rows=[official,institution,{...official},member({id:'other',name:'Other Official',organization_ids:['elsewhere'],organization_id:'elsewhere'})];
  assert.deepEqual(view.filterMembers(rows,{scope:'officials',organization:'parent'},organizations).map(m=>m.id),['official']);
  assert.deepEqual(view.filterMembers(rows,{scope:'institutions'},organizations).map(m=>m.id),['agency']);
  assert.deepEqual(view.filterMembers(rows,{scope:'officials',organization:'task',search:'CHILD'},organizations).map(m=>m.id),['official']);
  assert.deepEqual(view.filterMembers(rows,{scope:'officials',search:'absent'},organizations),[]);
  assert.deepEqual(view.filterMembers(rows,{},organizations).map(m=>m.id),['official','other']);
});

test('distribution uses the filtered cohort and excludes pending, missing, and no-evidence values', () => {
  const rows=[member(),member({id:'half',scores:{ai_overall:2.5}}),
    member({id:'pending',n_labeled:2,status:'partial',scores:{ai_overall:0}}),
    member({id:'none',status:'no_evidence',n_statements:0,n_labeled:0,scores:{ai_overall:0}}),
    member({id:'missing',scores:{ai_overall:null}}),member({id:'invalid',scores:{ai_overall:'3'}})];
  const result=view.scoreDistribution(rows,'ai_overall');
  assert.equal(result.total,6);
  assert.equal(result.scored,2);
  assert.equal(result.pending,1);
  assert.equal(result.no_evidence,1);
  assert.equal(result.unavailable,2);
  assert.deepEqual(result.bins.map(b=>[b.score,b.count]),[[0,0],[1,0],[2,1],[3,1],[4,0]]);
});

test('silence zeros are explicit and incomplete evidence cannot become silence', () => {
  assert.equal(view.scoreState(member(), 'x_risk').label,'0 · No discussion');
  assert.equal(view.scoreState(member({status:'partial',n_labeled:1}), 'x_risk').kind,'pending');
  assert.equal(view.scoreState(member({status:'no_evidence',n_statements:0,n_labeled:0}), 'x_risk').label,'No evidence');
  assert.equal(view.scoreState(member({scores:{}}), 'x_risk').label,'Not enough evidence: no statements on this question');
  assert.equal(view.scoreState(member({status:'partial'}), 'x_risk').label,'0 · No discussion');
  assert.equal(view.scoreState(member({scores:{regulation:0},score_details:{regulation:{reason_a:'consistent',reason_b:'consistent'}}}), 'regulation').label,'0 · Opposes AI rules');
  assert.equal(view.scoreState(member({scores:{regulation:null},score_details:{regulation:{reason_a:'no_statements',reason_b:'no_statements'}}}), 'regulation').label,'Not enough evidence: no statements on this question');
  assert.equal(view.scoreState(member({scores:{x_risk:0},score_details:{}}), 'x_risk').label,'0');
});

test('score colors use the same nearest-whole bands as Congress',()=>{
  const result=view.scoreDistribution([member({scores:{ai_overall:2.2}}),member({scores:{ai_overall:2.5}})],'ai_overall');
  assert.equal(result.bins[2].count,1);
  assert.equal(result.bins[3].count,1);
});

test('detail data must match the eligible profile, revision, and exact source count', () => {
  const m=member({n_statements:1});
  const data={schema_version:1,revision:'r1',members:[m]};
  const detail={schema_version:1,id:m.id,revision:'r1',profile:m,statements:[{sid:'s1'}],history:[],changes:[]};
  assert.equal(view.validateDetail(detail,m,data),detail);
  assert.throws(()=>view.validateDetail({...detail,revision:'old'},m,data),/stale/i);
  assert.throws(()=>view.validateDetail({...detail,id:'excluded'},m,data),/stale/i);
  assert.throws(()=>view.validateDetail({...detail,statements:[]},m,data),/stale/i);
  assert.throws(()=>view.validateDetail(detail,m,{...data,members:[]}),/stale/i);
});

test('source quotes escape text, retain attribution and assessments, and reject executable links', () => {
  const html=view.renderStatement({sid:'s1',date:'2025',url:'javascript:alert(1)',text:'<img src=x onerror=alert(1)>',
    source_type:'web',attribution:{kind:'institutional',speaker:'Agency',note:'A joint statement.'},
    analysis:{status:'complete',a:{ai_overall:2},b:{ai_overall:3},confidence:{ai_overall:3},escalated:['ai_overall'],
      topics:['safety'],models:{deepseek:'deepseek/model',sol:'openai/model'}}},dimensions);
  assert.match(html,/&lt;img/);
  assert.doesNotMatch(html,/<img|href="javascript:/);
  assert.match(html,/Institutional statement/);
  assert.match(html,/year only/);
  assert.match(html,/3 of 5/);
  assert.match(html,/deepseek\/model/);
  assert.match(html,/AI overall/);
  assert.equal(view.safeURL('data:text/html,bad'),null);
  assert.equal(view.safeURL('/local'),null);
  assert.equal(view.safeURL('https://example.gov/quote'), 'https://example.gov/quote');
});

test('Astra review exposes support, confidence, and the final-judge override safely', () => {
  const review={accepted:true,labels:{ai_overall:4},confidence:{ai_overall:3},review_confidence:3,
    reason:'Broad <benefits>.',support_basis:'context',supporting_quote:'AI helps <people>.',
    source_context:{url:'javascript:alert(1)',quote:'AI helps <people>.'},model:'openai/gpt-6-astra',assessed_at:'2026-11-09'};
  const html=view.renderStatement({sid:'s1',text:'Original quote',analysis:{status:'complete',stance_review:review}},dimensions);
  assert.match(html,/Astra stance review/);
  assert.match(html,/3 of 5/);
  assert.match(html,/AI helps &lt;people&gt;/);
  assert.match(html,/both AI overall columns/);
  assert.doesNotMatch(html,/href="javascript:|<people>|<benefits>/);
  const profile=view.renderStanceReview({status:'complete',reason:'No broad stance.',n_statements:4,n_contexts:2,
    confidence:4,accepted_sids:[],assessed_at:'2026-11-09',model:'openai/gpt-6-astra'},[]);
  assert.match(profile,/4 statements/);
  assert.match(profile,/No qualifying stance/);
});

test('citation links resolve only inside the current profile and incomplete summaries remain explicit', () => {
  const statements=[{sid:'s1',text:'A quote'}];
  const html=view.renderSummary({status:'complete',text:'A <claim>.',sids:['s1','someone_else']},statements);
  assert.match(html,/A &lt;claim&gt;/);
  assert.match(html,/href="#quote-s1"/);
  assert.doesNotMatch(html,/href="#quote-someone_else"/);
  assert.match(html,/unavailable citation/i);
  assert.match(view.renderSummary({status:'pending',text:'',sids:[]},statements),/Summary pending/);
  assert.match(view.renderStatement({sid:'s2',text:'Unlabeled',analysis:{status:'pending'}},dimensions),/Assessment pending/);
});

test('sentence-level summaries place each citation beside its supported sentence', () => {
  const html=view.renderSummary({status:'complete',text:'First claim. Second claim.',sids:['s1','s2'],
    sentences:[{text:'First claim.',sids:['s1']},{text:'Second claim.',sids:['s2']}]},[{sid:'s1'},{sid:'s2'}]);
  assert.ok(html.indexOf('First claim.') < html.indexOf('href="#quote-s1"'));
  assert.ok(html.indexOf('href="#quote-s1"') < html.indexOf('Second claim.'));
  assert.ok(html.indexOf('Second claim.') < html.indexOf('href="#quote-s2"'));
});

test('topic charts preserve fractional statement shares', () => {
  const split=view.renderTopics(member({n_statements:1,n_labeled:1,topics:{safety:0.5,economy:0.5}}),['safety','economy']);
  assert.deepEqual([...split.matchAll(/<strong>([^<]+)<\/strong>/g)].map(match=>match[1]),['0.5','0.5']);
  const html=view.renderTopics(member({n_statements:2,n_labeled:2,topics:{safety:0.5,economy:1.5}}),['safety','economy']);
  assert.deepEqual([...html.matchAll(/<strong>([^<]+)<\/strong>/g)].map(match=>match[1]),['0.5','1.5']);
  const widths=[...html.matchAll(/style="width:([\d.]+)%"/g)].map(match=>Number(match[1]));
  assert.ok(Math.abs(widths[0]-100/3)<0.001);
  assert.equal(widths[1],100);
  // the explanation of split weights now lives in the page's method section, not next to the chart
});

test('regulation areas distinguish completed no stance from unfinished assessments', () => {
  const areas=[{id:'testing',title:'Safety tests',group:'Frontier risk'}, {id:'chips',title:'Chip controls',group:'Trade'}];
  const html=view.renderRegulation({status:'complete',areas:{testing:{stance:2,why:'Calls for a test.',sids:['s1']}}},areas,[{sid:'s1'}]);
  assert.match(html,/Explicit support/);
  assert.match(html,/No stated position/);
  assert.match(html,/href="#quote-s1"/);
  assert.match(view.renderRegulation({status:'pending',areas:{}},areas,[]),/Assessment pending/);
  assert.doesNotMatch(view.renderRegulation({status:'pending',areas:{}},areas,[]),/No stated position/);
});

test('history separates reconstructed and observed records and leaves gaps for unknown scores', () => {
  const history=[{date:'2025-02-28',kind:'reconstructed',status:'complete',scores:{x_risk:0},n_statements:4},
    {date:'2025-01-31',kind:'reconstructed',status:'partial',scores:{x_risk:null},n_statements:2},
    {date:'2026-11-08',kind:'observed',status:'complete',scores:{x_risk:3},n_statements:4},
    {date:'not-a-date',kind:'observed',status:'complete',scores:{x_risk:4}}];
  assert.deepEqual(view.historySeries(history,'x_risk','reconstructed').map(p=>[p.date,p.value]),[
    ['2025-01-31',null],['2025-02-28',0]]);
  const html=view.renderHistory(history,'x_risk','Catastrophic risk');
  assert.match(html,/Reconstructed history/);
  assert.match(html,/Observed snapshots/);
  assert.match(html,/Assessment pending/);
  assert.match(view.dateLabel('2025-03'),/day unknown/);
  assert.equal(view.dateLabel(null),'Date unknown');
  assert.equal(view.dateLabel('2025-02-30'),'Date unknown');
});

test('empty profiles distinguish pending web research from a completed search', () => {
  const empty=member({status:'no_evidence',n_statements:0,n_labeled:0,scores:{ai_overall:null}});
  const unsearched={...empty,research:{research_status:'not_started'}};
  const partial={...empty,research:{research_status:'in_progress',completed_passes:2}};
  const searched={...empty,research:{research_status:'searched',completed_passes:8}};
  assert.equal(view.scoreState(unsearched,'ai_overall').kind,'research_pending');
  assert.equal(view.scoreState(partial,'ai_overall').value,null);
  assert.equal(view.scoreState(searched,'ai_overall').kind,'searched_empty');
  assert.equal(view.scoreState(empty,'ai_overall').kind,'no_evidence');
  const result=view.scoreDistribution([unsearched,partial,searched,empty],'ai_overall');
  assert.equal(result.research_pending,2);
  assert.equal(result.searched_empty,1);
  assert.equal(result.bins[0].count,0);
});

test('profile status separates model progress, a narrow record, and daily check dates', () => {
  const narrow=member({scores:{ai_overall:null,regulation:2},score_details:{ai_overall:{reason_a:'no_statements',reason_b:'no_statements'}},
    research:{research_status:'searched',completed_passes:8,official_leads_pending:2,daily:{web:{named_query:'Official',pending_named_queries:1,last_success_on:'2026-11-08'},
      x:{last_successful_cutoff:'2026-11-09T18:17:32Z',pending_windows:2}}}});
  const html=view.renderProfileCoverage(narrow);
  assert.match(html,/Assessment complete/);
  assert.match(html,/No qualifying AI overall stance/);
  assert.match(html,/Historical web passes complete/);
  assert.match(html,/2 official source leads pending/);
  assert.match(html,/Daily named web query queued/);
  assert.match(html,/Last successful web check: 2026-11-08/);
  assert.match(html,/2026-11-09 18:17 UTC/);
  assert.match(html,/2 X windows pending/);
  assert.equal(view.scoreState(narrow,'ai_overall').value,null);
  assert.equal(view.scoreState(narrow,'regulation').value,2);
  const pending=member({...narrow,n_labeled:1,status:'partial'});
  const pendingHTML=view.renderProfileCoverage(pending);
  assert.match(pendingHTML,/Assessments pending/);
  assert.doesNotMatch(pendingHTML,/No qualifying AI overall stance/);
});

test('coverage overview reports pending research and distinguishes the shared queue from successful checks', () => {
  const profiles=[member({n_statements:0,n_labeled:0,research:{research_status:'not_started'}}),
    member({n_statements:0,n_labeled:0,research:{research_status:'searched'}}),member({status:'partial',n_labeled:2})];
  const coverage={daily:{web:{pending_named_queries:9,pending_pages:12,last_named_success_on:'2026-11-08',
    oldest_known_pending_on:null},x:{pending_windows:3}}};
  const html=view.renderResearchCoverage(coverage,profiles);
  assert.match(html,/1 web research pending/);
  assert.match(html,/1 searched with no verified evidence/);
  assert.match(html,/1 with assessments pending/);
  assert.match(html,/9 named web queries due/);
  assert.match(html,/12 pages queued/);
  assert.match(html,/Last successful named web check: 2026-11-08/);
  assert.match(html,/Oldest queue date unknown/);
  assert.match(html,/Collection limits can leave profiles pending across days/);
});

test('reported roles expose escaped title notes and safe additional sources', () => {
  const html=view.renderRoles({roles:[{title:'Acting Director <example>',status:'historical',source_type:'reporting',
    title_note:'The organization chart says <Acting>.',source_url:'https://example.gov/chart?a=1&b=2',
    additional_source_urls:['javascript:alert(1)','https://example.gov/bio?one=1&two=2','data:text/html,bad']}]});
  assert.match(html,/Acting Director &lt;example&gt;/);
  assert.match(html,/historical role/);
  assert.match(html,/reported role/);
  assert.match(html,/says &lt;Acting&gt;/);
  assert.match(html,/href="https:\/\/example.gov\/chart\?a=1&amp;b=2"/);
  assert.match(html,/href="https:\/\/example.gov\/bio\?one=1&amp;two=2"/);
  assert.doesNotMatch(html,/javascript:|data:text\/html|<Acting>/);
});


test('new X mappings show a daily check due before any window enters the saved queue', () => {
  const x={accounts_due_for_daily_check:1,pending_windows:0,last_successful_cutoff:null};
  const profile=member({research:{research_status:'not_started',daily:{x}}});
  const detail=view.renderProfileCoverage(profile);
  assert.match(detail,/Daily X check due/);
  assert.match(detail,/Last successful X cutoff: Unknown/);
  const overview=view.renderResearchCoverage({daily:{x}},[profile]);
  assert.match(overview,/1 X account due for a daily check/);
  assert.match(overview,/0 saved X windows pending/);
});
