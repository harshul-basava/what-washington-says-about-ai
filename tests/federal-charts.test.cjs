const test = require('node:test');
const assert = require('node:assert/strict');
const charts = require('../site/federal-charts.js');
const person = (id, overrides={}) => ({id,name:id,entity_type:'person',organization_id:'child',
  organization_ids:['child','task'],organization_name:'Child',n_statements:4,n_labeled:4,status:'complete',
  scores:{x_risk:3,regulation:2},regulation:{status:'complete',areas:{}},...overrides});
const organizations=[{id:'parent',name:'Department'},{id:'child',name:'Child',parent_id:'parent'},{id:'task',name:'Task force'}];

test('agency comparison counts each primary affiliation once and uses all profiles',()=>{
  const rows=charts.agencyDistribution([person('a'),person('b',{scores:{x_risk:2.2}}),
    person('c',{n_labeled:0,scores:{x_risk:4}})],'x_risk',organizations);
  assert.equal(rows.length,1);
  assert.equal(rows[0].id,'parent');
  assert.equal(rows[0].total,3);
  assert.deepEqual(rows[0].bins,[0,0,1,1,0]);
  assert.equal(rows[0].missing,1);
});
test('policy bars preserve explicit and implied stances with unknowns outside stance totals',()=>{
  const m=(id,stance,status='complete')=>person(id,{regulation:{status,areas:{test:{stance}}}});
  const row=charts.policyDistribution([m('a',2),m('b',-1),m('c',0),m('d',2,'pending')],[{id:'test',title:'Tests'}])[0];
  assert.deepEqual(row.counts,{'-2':0,'-1':1,'0':1,'1':0,'2':1});
  assert.equal(row.total,4);assert.equal(row.unknown,1);
});
test('timeline keeps current cohort denominator and separates observed dates from reconstructed dates',()=>{
  const data={a:{history:[{date:'2025-01-31',kind:'reconstructed',status:'complete',scores:{x_risk:3}},
    {date:'2025-02-01',kind:'observed',status:'complete',scores:{x_risk:4}}]},
    b:{history:[{date:'2025-01-31',kind:'reconstructed',status:'pending',scores:{x_risk:4}}]}};
  const result=charts.cohortHistory([person('a'),person('b')],data,'x_risk','reconstructed');
  assert.deepEqual(result,[{date:'2025-01-31',high:1,scored:1,total:2,percent:50}]);
  assert.equal(charts.cohortHistory([person('b')],data,'x_risk','reconstructed')[0].percent,0);
  assert.equal(charts.cohortHistory([person('a')],data,'x_risk','observed').length,1);
});
test('rolling topic shares split each statement and count the exact 30-day window',()=>{
  const profiles={a:{topics:[{date:'2025-01-01',topics:['safety']},{date:'2025-01-02',topics:['safety','jobs']},
    {date:'2025-01-31',topics:['jobs']}]},outside:{topics:[{date:'2025-01-31',topics:['safety']}]}};
  const result=charts.topicTimeline([person('a')],profiles,['safety','jobs'],'2025-01-31','2025-01-31');
  assert.equal(result.length,1);assert.equal(result[0].total,2);
  assert.deepEqual(result[0].shares,{safety:25,jobs:75});
  assert.equal(charts.topicTimeline([],profiles,['safety'],'2025-01-31','2025-01-31')[0].shares.safety,null);
});
test('comparison scatter and presets do not convert missing scores to zero',()=>{
  const rows=[person('a',{scores:{x_risk:3,regulation:1}}),person('b',{scores:{x_risk:3,regulation:null}})];
  assert.deepEqual(charts.comparisonPoints(rows,'x_risk','regulation').map(m=>m.id),['a']);
  assert.deepEqual(charts.presetMembers(rows,'risk_low_rules').map(m=>m.id),['a']);
});
test('chart payload must match the index revision and eligible IDs',()=>{
  const data={revision:'new',members:[person('a')]};
  const payload={schema_version:1,revision:'new',profiles:{a:{history:[],topics:[],changes:[]}}};
  assert.equal(charts.validateCharts(payload,data),payload);
  assert.throws(()=>charts.validateCharts({...payload,revision:'old'},data),/stale/i);
  assert.throws(()=>charts.validateCharts({...payload,profiles:{...payload.profiles,excluded:{}}},data),/stale/i);
});

test('an empty dot chart does not present a zero-percent policy result',()=>{
  const html=charts.renderDots([],'x_risk');
  assert.match(html,/No profiles/);
  assert.doesNotMatch(html,/% score/);
});

test('gray profile counts separate a missing stance from sparse evidence and pending reviews',()=>{
  const rows=[person('scored'),
    person('silent',{scores:{regulation:null},score_details:{regulation:{reason_a:'no_statements',reason_b:'no_statements'}}}),
    person('sparse',{n_statements:2,n_labeled:2,scores:{regulation:null}}),
    person('none',{n_statements:0,n_labeled:0,status:'no_evidence',scores:{regulation:null}}),
    person('pending',{n_labeled:1,status:'partial',scores:{regulation:null}})];
  const result=charts.scoreAvailability(rows,'regulation');
  assert.equal(result.total,5);assert.equal(result.scored,1);
  assert.deepEqual(Object.fromEntries(result.groups.map(g=>[g.id,g.members.map(m=>m.id)])),{
    no_stance:['silent'],insufficient_evidence:['sparse'],no_evidence:['none'],pending:['pending']
  });
  const html=charts.renderAvailability(rows,{id:'regulation',title:'Regulation'});
  assert.match(html,/1 of 5 profiles have a score/);
  assert.match(html,/No qualifying stance/);
  assert.match(html,/Fewer than three verified excerpts/);
  assert.match(html,/No verified excerpts/);
  assert.match(html,/Assessment pending/);
  assert.match(html,/data-profile="silent"/);
});

test('a silence zero remains scored under the congressional intensity rules',()=>{
  const m=person('silent',{scores:{x_risk:0},score_details:{x_risk:{reason_a:'silent',reason_b:'silent'}}});
  const result=charts.scoreAvailability([m],'x_risk');
  assert.equal(result.scored,1);assert.deepEqual(result.groups,[]);
});

test('recent changes list only moves of more than 1 point between two scores',()=>{
  const html=charts.renderRecent([person('a')],{a:{changes:[{date:'2026-11-09',dimension:'ai_overall',old:null,new:3,cause:'Astra review'},
    {date:'2026-11-08',dimension:'ai_overall',old:1,new:3,cause:'new statements'},{date:'2026-11-07',dimension:'ai_overall',old:2,new:3,cause:'small'}]}},'ai_overall','2026-11-09');
  assert.doesNotMatch(html,/Unscored → 3/);
  assert.match(html,/1 → 3/);
  assert.doesNotMatch(html,/small/);
});

test('unsearched, searched empty, and narrow completed profiles stay outside score bins',()=>{
  const empty={n_statements:0,n_labeled:0,status:'no_evidence',scores:{ai_overall:null}};
  const members=[person('unsearched',{...empty,research:{research_status:'not_started'}}),
    person('searched',{...empty,research:{research_status:'searched'}}),
    person('narrow',{scores:{ai_overall:null,regulation:2},research:{research_status:'searched'},score_details:{ai_overall:{reason_a:'silent',reason_b:'no_statements'}}})];
  const result=charts.scoreAvailability(members,'ai_overall');
  assert.equal(result.scored,0);
  assert.deepEqual(Object.fromEntries(result.groups.map(g=>[g.id,g.members.map(m=>m.id)])),{
    research_pending:['unsearched'],searched_empty:['searched'],no_stance:['narrow']
  });
  const distribution=charts.agencyDistribution(members,'ai_overall',organizations)[0];
  assert.equal(distribution.missing,3);
  assert.deepEqual(distribution.bins,[0,0,0,0,0]);
  const table=charts.renderMembers(members,[{id:'ai_overall',title:'AI overall'}]);
  assert.match(table,/Web research pending/);
  assert.match(table,/Searched · no verified evidence/);
  assert.match(table,/No qualifying AI overall stance/);
  assert.equal((table.match(/fc-score-chip fc-missing/g)||[]).length,3);
});
