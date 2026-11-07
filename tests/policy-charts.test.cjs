const test = require('node:test');
const assert = require('node:assert/strict');
const charts = require('../site/policy-charts.js');
const member = (id, stance, coverage='complete', relevant=1, party='Democrat') =>
  ({id, party, policies:{p:{stance, coverage, relevant}}});

test('member charts keep no evidence and pending work out of the stance denominator', () => {
  const result = charts.breakdown([
    member('A','support'), member('B','disputed'), member('C',null,'no_matching_evidence',0),
    member('D',null,'no_relevant_evidence',0), member('E','oppose','partial'), member('F',null,'pending',0)
  ], 'p');
  assert.equal(result.total,6);
  assert.equal(result.observed,2);
  assert.equal(result.missing,2);
  assert.equal(result.pending,2);
  assert.equal(result.counts.support,1);
  assert.equal(result.counts.oppose,0);
  assert.equal(result.counts.disputed,1);
  assert.equal(charts.breakdown([], 'p').observed,0);
});

test('timeline preserves gaps and excludes dates too imprecise for the chosen period', () => {
  const rows = [
    {person_id:'A',date:'2026-07-23',stance:'support'},
    {person_id:'A',date:'2026-07',stance:'support'},
    {person_id:'B',date:'2026-09-02',stance:'oppose'},
    {person_id:'B',date:'2026',stance:'support'},
    {person_id:'A',date:null,stance:'disputed'},
    {person_id:'A',date:'2026-02-30',stance:'support'},
    {person_id:'A',date:'2026-09-01',stance:'not_relevant'},
    {person_id:'A',date:'2026-09-01',stance:'pending'}
  ];
  const result = charts.timeline(rows);
  assert.equal(result.granularity,'month');
  assert.equal(result.excludedDates,3);
  assert.equal(result.pending,1);
  assert.deepEqual(result.periods.map(p=>p.key),['2026-07','2026-08','2026-09']);
  assert.deepEqual(result.periods.map(p=>p.total),[2,0,1]);
  assert.equal(result.periods[0].people,1);
  assert.equal(result.periods[2].counts.oppose,1);
  assert.equal(charts.timeline([]).periods.length,0);
});

test('long timelines use calendar quarters with proportional intervening periods', () => {
  const result = charts.timeline([{date:'2023-01-01',stance:'support',person_id:'A'}, {date:'2026-10',stance:'mixed',person_id:'B'}]);
  assert.equal(result.granularity,'quarter');
  assert.equal(result.periods.length,16);
  assert.equal(result.periods[0].key,'2023-Q1');
  assert.equal(result.periods[15].key,'2026-Q4');
  assert.equal(result.periods[5].total,0);
});

test('detail counts distinguish joint labels from single-model labels without counting pending records', () => {
  const result = charts.facetCounts([
    {stance:'support',facets_agreed:['cooperation'],facets_disputed:['speed_over_safety']},
    {stance:'disputed',facets_agreed:[],facets_disputed:['cooperation']},
    {stance:'pending',facets_agreed:['cooperation'],facets_disputed:[]},
    {stance:'not_relevant',facets_agreed:[],facets_disputed:[]}
  ],['cooperation','speed_over_safety']);
  assert.deepEqual(result,[{id:'cooperation',agreed:1,disputed:1},{id:'speed_over_safety',agreed:0,disputed:1}]);
});

test('chart geometry stays finite for zero and sparse data and preserves sums', () => {
  assert.equal(charts.percent(0,0),0);
  assert.equal(charts.percent(1,4),25);
  assert.equal(charts.percent(5,4),100);
  const html = charts.stanceBar({counts:{support:8,disputed:1},observed:9});
  assert.ok(html.includes('8 support'));
  assert.ok(!html.includes('NaN'));
  assert.ok(!charts.stanceBar(charts.breakdown([], 'p')).includes('NaN'));
});

test('cascade detail bars count final labels by primary acceptance or Astra review', () => {
  const result=charts.facetCounts([
    {stance:'support',facets_final:['cooperation'],final_judge:'deepseek'},
    {stance:'oppose',facets_final:['cooperation'],final_judge:'astra'},
    {stance:'review_required',facets_final:[],final_judge:null},
    {stance:'pending',facets_final:[],final_judge:null},
  ],['cooperation']);
  assert.deepEqual(result,[{id:'cooperation',agreed:1,disputed:1}]);
  assert.equal(charts.timeline([{stance:'review_required'}]).pending,1);
});
