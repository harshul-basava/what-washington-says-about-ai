const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const raw = {data:{search_by_raw_query:{search_timeline:{timeline:{instructions:[]}}}}};
const worker = async () => {
  assert.ok(fs.existsSync('scripts/federal_x_worker.mjs'), 'Federal emusks worker is missing');
  return import('../scripts/federal_x_worker.mjs');
};

test('emusks normalization keeps author text and identity separate from quoted posts', async () => {
  const {normalizePage} = await worker();
  const result = normalizePage({id:'7',username:'Agency',protected:false}, {
    raw,tweets:[{id:'100',text:'Our own AI policy statement.',created_at:'2026-11-01T12:00:00Z',
      user:{id:'7',username:'Agency'},quoting:{text:'Another person supports a ban.'},retweeting:null}],nextCursor:'next'});
  assert.equal(result.posts[0].text,'Our own AI policy statement.');
  assert.equal(result.posts[0].author_id,'7');
  assert.equal(result.posts[0].is_repost,false);
  assert.equal(result.cursor,'next');
  assert.ok(!JSON.stringify(result).includes('Another person'));
});

test('emusks normalization rejects protected accounts and malformed pages', async () => {
  const {normalizePage} = await worker();
  assert.throws(()=>normalizePage({id:'7',username:'Agency',protected:true},{tweets:[]}));
  assert.throws(()=>normalizePage({id:'7',username:'Agency'},{}));
  assert.throws(()=>normalizePage({id:'7',username:'Agency'},{tweets:[],raw:{errors:[{message:'private body'}]}}));
  const result=normalizePage({id:'7',username:'Agency'},{raw,tweets:[{id:'100',text:'A repost',
    created_at:'2026-11-01T12:00:00Z',retweeting:{id:'90'},user:{id:'7',username:'Agency'}}]});
  assert.equal(result.posts[0].is_repost,true);
});

test('provider errors expose fixed codes without credentials or response bodies', async () => {
  const {errorCode} = await worker();
  assert.equal(errorCode(new Error('429 rate limit secret-token')),'rate_limited');
  assert.equal(errorCode(new Error('401 auth secret-token')),'authentication_failed');
  assert.equal(errorCode(new Error('payload secret-token')),'request_failed');
});

test('a changed provider payload cannot masquerade as an empty search', async () => {
  const {normalizePage}=await worker();
  assert.throws(()=>normalizePage({id:'7',username:'Agency'}, {tweets:[],nextCursor:null,
    raw:{data:{search_by_raw_query:{}}}}));
  assert.throws(()=>normalizePage({id:'7',username:'Agency'}, {raw,tweets:[{id:'100'}]}));
  assert.deepEqual(normalizePage({id:'7',username:'Agency'},{raw,tweets:[]}).posts,[]);
});

test('structured rate and authentication errors retain safe classifications', async () => {
  const {normalizePage,errorCode}=await worker();
  assert.equal(errorCode(Object.assign(new Error('Too many requests'),{status:429})),'rate_limited');
  assert.equal(errorCode({errors:[{code:88,message:'private payload'}]}),'rate_limited');
  assert.equal(errorCode({errors:[{code:89,message:'private payload'}]}),'authentication_failed');
  try {
    normalizePage({id:'7',username:'Agency'}, {tweets:[],raw:{...raw,errors:[{code:88,message:'private payload'}]}});
    assert.fail('Expected a provider error');
  } catch(error) {
    assert.equal(errorCode(error),'rate_limited');
    assert.ok(!error.message.includes('private payload'));
  }
});
