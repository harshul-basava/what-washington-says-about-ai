const test = require('node:test');
const assert = require('node:assert/strict');
const history = require('../site/congress-history.js');
const row = overrides => ({d:'2026-11-10',c:'119',p:'all',k:'x_risk',hi:1,scored:10,n:500,...overrides});

test('Congress history separates support among scored members from evidence coverage',()=>{
  const rows=history.series([row(),row({p:'D',hi:1,scored:2,n:100}),row({c:'120'}),row({k:'ai_overall'})],'119','x_risk');
  assert.equal(rows.length,2);
  const all=rows.find(r=>r.p==='all'),dem=rows.find(r=>r.p==='D');
  assert.equal(all.percent,10);assert.equal(all.coveragePercent,2);
  assert.equal(dem.percent,50);assert.equal(dem.coveragePercent,2);
});
test('Congress history preserves known zero and leaves missing denominators unavailable',()=>{
  const rows=history.series([row({p:'all',hi:0,scored:2}),row({p:'D',hi:0,scored:0}),
    row({p:'R',scored:undefined})],'119','x_risk');
  assert.equal(rows.find(r=>r.p==='all').percent,0);
  assert.equal(rows.find(r=>r.p==='D').percent,null);
  assert.equal(rows.find(r=>r.p==='D').coveragePercent,0);
  assert.equal(rows.find(r=>r.p==='R').percent,null);
  assert.equal(rows.find(r=>r.p==='R').coveragePercent,null);
  assert.equal(history.series([row({hi:3,scored:2})],'119','x_risk')[0].percent,null);
});
test('Congress timeline details retain decimal percentages and both counts',()=>{
  const html=history.details(history.series([row({scored:500})],'119','x_risk'));
  assert.match(html,/0\.2%/);assert.match(html,/100\.0%/);
  assert.match(html,/1 of 500/);assert.match(html,/500 of 500/);
  assert.match(html,/Evidence coverage/);
  assert.match(history.details(history.series([row({hi:0,scored:0})],'119','x_risk')),/No scored members/);
});
