const test = require('node:test');
const assert = require('node:assert/strict');
const view = require('../site/federal-analysis.js');

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
  assert.equal(view.scoreState(member({scores:{}}), 'x_risk').label,'Score unavailable');
  assert.equal(view.scoreState(member({status:'partial'}), 'x_risk').label,'0 · No discussion');
  assert.equal(view.scoreState(member({scores:{regulation:0},score_details:{regulation:{reason_a:'consistent',reason_b:'consistent'}}}), 'regulation').label,'0 · Opposes rules');
  assert.equal(view.scoreState(member({scores:{regulation:null},score_details:{regulation:{reason_a:'no_statements',reason_b:'no_statements'}}}), 'regulation').label,'No discussion');
  assert.equal(view.scoreState(member({scores:{x_risk:0},score_details:{}}), 'x_risk').label,'0');
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

test('topic charts preserve fractional statement shares and explain split attribution', () => {
  const split=view.renderTopics(member({n_statements:1,n_labeled:1,topics:{safety:0.5,economy:0.5}}),['safety','economy']);
  assert.deepEqual([...split.matchAll(/<strong>([^<]+)<\/strong>/g)].map(match=>match[1]),['0.5','0.5']);
  const html=view.renderTopics(member({n_statements:2,n_labeled:2,topics:{safety:0.5,economy:1.5}}),['safety','economy']);
  assert.deepEqual([...html.matchAll(/<strong>([^<]+)<\/strong>/g)].map(match=>match[1]),['0.5','1.5']);
  const widths=[...html.matchAll(/style="width:([\d.]+)%"/g)].map(match=>Number(match[1]));
  assert.ok(Math.abs(widths[0]-100/3)<0.001);
  assert.equal(widths[1],100);
  assert.match(html,/statement shares/i);
  assert.match(html,/split equally/i);
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
  assert.match(html,/No discussion can produce a zero/);
  assert.match(html,/Assessment pending/);
  assert.match(view.dateLabel('2025-03'),/day unknown/);
  assert.equal(view.dateLabel(null),'Date unknown');
  assert.equal(view.dateLabel('2025-02-30'),'Date unknown');
});
