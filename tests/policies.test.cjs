const test = require('node:test');
const assert = require('node:assert/strict');
const view = require('../site/policies.js');

test('federal update notes distinguish missing, complete, and partial attempts', () => {
  assert.match(view.federalUpdateNote(null), /No automated federal update/);
  assert.match(view.federalUpdateNote({date:'2026-11-08',status:'ok'}), /completed/);
  const partial = view.federalUpdateNote({date:'2026-11-08',status:'partial',collection:{pending_pages:3},judgments:{pending_pairs:2}});
  assert.match(partial, /partial/);
  assert.match(partial, /3 source pages/);
  assert.match(partial, /2 judgments/);
});

test('filters use explicit stances without converting absent evidence to opposition', () => {
  const members = [
    {name:'Alice', state:'CA', party:'Democrat', status:'current', policies:{p:{stance:'support', coverage:'complete', relevant:2}}},
    {name:'Bob', state:'TX', party:'Republican', status:'current', policies:{p:{stance:null, coverage:'no_matching_evidence', relevant:0}}},
    {name:'Cara', state:'CA', party:'Democrat', status:'member_elect', policies:{p:{stance:'oppose', coverage:'complete', relevant:1}}},
  ];
  assert.deepEqual(view.filterMembers(members, {policy:'p', stance:'oppose'}).map(m=>m.name), ['Cara']);
  assert.deepEqual(view.filterMembers(members, {policy:'p', party:'R'}).map(m=>m.name), ['Bob']);
  assert.deepEqual(view.filterMembers(members, {policy:'p', search:'CA', population:'current'}).map(m=>m.name), ['Alice']);
  assert.deepEqual(view.filterMembers(members, {policy:'p', stance:'no_evidence'}).map(m=>m.name), ['Bob']);
});

test('source text and URLs cannot introduce executable markup', () => {
  const html = view.renderRecord({text:'<img src=x onerror=alert(1)>', url:'javascript:alert(1)', date:null,
    source_type:'web', stance:'disputed', judges:{sonnet:{stance:'support',reason:'<script>bad</script>',facets:[]},
    gpt:{stance:'oppose',reason:'It rejects the proposal.',facets:[]}}});
  assert.ok(html.includes('&lt;img'));
  assert.ok(!html.includes('href="javascript:'));
  assert.ok(!html.includes('<script>'));
  assert.ok(html.includes('Support'));
  assert.ok(html.includes('Oppose'));
  assert.ok(html.includes('Models disagree'));
});

test('coverage labels separate unprocessed evidence from no evidence', () => {
  assert.equal(view.summaryLabel({stance:null,coverage:'pending'}), 'Assessment pending');
  assert.equal(view.summaryLabel({stance:null,coverage:'no_matching_evidence'}), 'No matching evidence');
  assert.equal(view.summaryLabel({stance:null,coverage:'no_relevant_evidence'}), 'No relevant evidence');
  assert.equal(view.summaryLabel({stance:'support',coverage:'partial'}), 'Support · partial assessment');
});

test('facet disagreements remain visible when stance agrees', () => {
  const html = view.renderRecord({text:'We must compete.', url:'https://example.org', stance:'support', facet_disagreement:true, judges:{}});
  assert.ok(html.includes('Models disagree on the details'));
  assert.equal(view.summaryLabel({stance:'support',coverage:'complete',facet_disagreements:1}), 'Support · details disputed');
});

test('missing or stale detail data does not become absence of evidence', () => {
  const member = {id:'P', policies:{p:{candidates:1}}};
  assert.throws(()=>view.evidenceRecords({id:'P',policies:{}},member,'p'));
  assert.throws(()=>view.evidenceRecords({id:'P',policies:{p:[]}},member,'p'));
  assert.throws(()=>view.evidenceRecords({id:'Q',policies:{p:[{}]}},member,'p'));
  assert.deepEqual(view.evidenceRecords({id:'P',policies:{p:[{text:'Quote'}]}},member,'p'),[{text:'Quote'}]);
});

test('cascade quote shows both confidence scores and the final reviewer without renaming DeepSeek', () => {
  const html=view.renderRecord({text:'A quote',url:'https://example.org',stance:'oppose',strategy:'confidence_cascade',
    final_judge:'astra',confidence:0.93,model_disagreement:true,review_status:'astra_reviewed',review_reason:'Below threshold.',
    judges:{deepseek:{stance:'support',reason:'Initial view.',facets:[],confidence:0.7,confidence_reason:'Ambiguous.'},
      astra:{stance:'oppose',reason:'Final view.',facets:[],confidence:0.93,confidence_reason:'Explicit rejection.'}}});
  assert.ok(html.includes('DeepSeek'));
  assert.ok(html.includes('Astra'));
  assert.ok(html.includes('0.7'));
  assert.ok(html.includes('0.93'));
  assert.ok(html.includes('Final assessment: Astra'));
  assert.ok(html.includes('Below threshold.'));
  assert.ok(!html.includes('GPT:'));
});

test('human review status stays visible instead of becoming no evidence', () => {
  assert.ok(view.summaryLabel({stance:null,coverage:'pending',human_review:1}).includes('human review'));
  const html=view.renderRecord({text:'Uncertain quote',url:'https://example.org',stance:'review_required',
    strategy:'confidence_cascade',review_status:'human_review_required',review_reason:'Both uncertain.',judges:{}});
  assert.ok(html.includes('Human review required'));
});

test('scope and membership filters keep officials unique and separate from institutions', () => {
  const base={policies:{p:{stance:null,coverage:'no_matching_evidence'}},roles:[]};
  const rows=[{...base,id:'C',name:'Congress member',branch:'legislative',entity_type:'person',party:'Independent'},
    {...base,id:'E',name:'Official',branch:'executive',entity_type:'person',party:null,organization_name:'Commerce',
      organization_ids:['commerce','task_force'],roles:[{organization_id:'commerce'},{organization_id:'task_force'}]},
    {...base,id:'O',name:'Commerce',branch:'executive',entity_type:'institution',organization_ids:['commerce']}];
  assert.deepEqual(view.filterMembers(rows,{policy:'p',scope:'executive',organization:'task_force'}).map(r=>r.id),['E']);
  assert.deepEqual(view.filterMembers(rows,{policy:'p',scope:'institutions'}).map(r=>r.id),['O']);
  assert.deepEqual(view.filterMembers(rows,{policy:'p',scope:'congress'}).map(r=>r.id),['C']);
  assert.deepEqual(view.filterMembers(rows,{policy:'p',party:'I'}).map(r=>r.id),['C']);
  assert.deepEqual(view.filterMembers(rows,{policy:'p',scope:'executive',search:'commerce'}).map(r=>r.id),['E']);
});

test('official and institutional attribution appears beside source quotes', () => {
  const html=view.renderRecord({text:'An official quote',url:'https://example.gov',stance:'support',judges:{},
    attribution:{kind:'official_role',speaker:'Speaker',role:'Secretary',note:'A named quote.'}});
  assert.ok(html.includes('Official role'));
  assert.ok(html.includes('Secretary'));
  const institutional=view.renderRecord({text:'Agency statement',stance:'neutral',judges:{},
    attribution:{kind:'institutional',speaker:'Agency',note:'Joint statement; not a personal position.'}});
  assert.ok(institutional.includes('Institutional statement'));
  assert.ok(institutional.includes('Joint statement'));
});

test('profiles show sourced roles and explicit unknown dates without implying independent party affiliation', () => {
  const html=view.renderProfile({id:'E',name:'Official',entity_type:'person',branch:'executive',roles:[
    {title:'Chair',organization_id:'task',start_date:null,end_date:null,verified_on:'2026-11-07',source_url:'https://example.gov/role'}]},
    [{id:'task',name:'Task force'}],[]);
  assert.ok(html.includes('Chair'));
  assert.ok(html.includes('Start date unknown'));
  assert.ok(html.includes('2026-11-07'));
  assert.ok(html.includes('https://example.gov/role'));
  assert.ok(!html.includes('Independent'));
  assert.deepEqual(view.evidenceRecords({id:'E',policies:{}},{id:'E',policies:{p:{candidates:0}}},'p'),[]);
});

test('unmatched source library never presents an unmade relevance judgment', () => {
  const html=view.renderRecord({text:'A source',url:'https://example.gov',library_only:true,stance:'not_relevant',judges:{}});
  assert.ok(html.includes('No policy assessment'));
  assert.ok(!html.includes('Not relevant'));
});

test('historical coverage reports search effort and gaps separately from model confidence', () => {
  const html=view.renderProfile({id:'E',name:'Official',entity_type:'person',branch:'executive',roles:[],
    research:{statements:3,sources:2,completed_passes:8,research_status:'searched',gaps:['No <script> source.']}},[],[]);
  assert.ok(html.includes('3 verified excerpts'));
  assert.ok(html.includes('8 completed search passes'));
  assert.ok(html.includes('No &lt;script&gt; source.'));
  assert.ok(!html.includes('8%'));
});

test('federal coverage distinguishes configured X search from completed collection', () => {
  const research={summary:{people:150,people_searched:150,people_median_statements:5,
    congress_median_statements:12,people_without_evidence:11,x_accounts:23,x_mapped_profiles:20,x_statements:0},
    x:{status:'unavailable',error:'missing_auth_token'}};
  const note=view.researchCoverageNote(research);
  assert.ok(note.includes('23 sourced X accounts'));
  assert.ok(note.includes('0 X excerpts'));
  assert.ok(note.includes('requires authentication'));
  assert.ok(!note.includes('complete X archive'));
});

test('federal coverage names the official provider without relabeling old evidence', () => {
  const note=view.researchCoverageNote({summary:{people:150,people_searched:150,people_median_statements:6,
    congress_median_statements:12,people_without_evidence:11,x_accounts:23,x_mapped_profiles:21,x_statements:1114},
    x:{provider:'x_api',status:'not_started'}});
  assert.ok(note.includes('Official X API'));
  assert.ok(note.includes('1114 X excerpts'));
  assert.ok(note.includes('has not started'));
  assert.ok(!note.includes('Emusks search has'));
});
