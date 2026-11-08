// Read-only emusks bridge. Credentials stay in the environment, never in JSON or logs.
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

export function errorCode(error) {
  if (['malformed_response','rate_limited','authentication_failed'].includes(error?.code)) return error.code;
  const status=Number(error?.status || error?.statusCode || error?.response?.status);
  const codes=[error?.code,...(Array.isArray(error?.errors) ? error.errors.map(e=>e?.code) : [])].map(Number);
  if (status===429 || codes.includes(88)) return 'rate_limited';
  if ([401,403].includes(status) || codes.some(code=>[32,89,215,239,326].includes(code))) return 'authentication_failed';
  const message = String(error?.message || '');
  if (/429|rate.?limit|code.?88\b/i.test(message)) return 'rate_limited';
  if (/401|403|auth|login|session|code.?32\b|code.?89\b/i.test(message)) return 'authentication_failed';
  if (/timeout|timed.?out/i.test(message)) return 'timeout';
  return 'request_failed';
}

export function normalizePage(account, result) {
  if (!/^\d+$/.test(account?.id || '') || !/^[A-Za-z0-9_]{1,15}$/.test(account?.username || '') || account.protected)
    throw new Error('Invalid public account');
  const errors=[...(result?.raw?.errors || []),...(result?.errors || [])];
  if (errors.length) throw Object.assign(new Error('Provider request failed'),{code:errorCode({errors})});
  const instructions=result?.raw?.data?.search_by_raw_query?.search_timeline?.timeline?.instructions;
  const validTweet=t=>typeof t?.id==='string' && /^\d+$/.test(t.id) && typeof t.text==='string' &&
    typeof t.created_at==='string' && Number.isFinite(Date.parse(t.created_at)) &&
    typeof t.user?.id==='string' && /^\d+$/.test(t.user.id) && /^[A-Za-z0-9_]{1,15}$/.test(t.user.username || '');
  if (!Array.isArray(instructions) || !Array.isArray(result?.tweets) || !result.tweets.every(validTweet) ||
      (result.nextCursor != null && typeof result.nextCursor !== 'string'))
    throw Object.assign(new Error('Invalid search page'),{code:'malformed_response'});
  return {account:{id:account.id,username:account.username},cursor:result.nextCursor || null,
    posts:result.tweets.map(t=>({id:t.id,text:t.text,created_at:t.created_at,
      author_id:t.user?.id,author:t.user?.username,is_repost:!!t.retweeting,
      is_promoted:!!(t.promotedMetadata || t.promoted_metadata || t.ad),
      restricted:!!(t.subscriber_only || t.user?.protected),is_reply:!!t.in_reply_to_status_id}))};
}

async function main() {
  const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
  try { process.loadEnvFile(path.join(root,'.env')); } catch(e) { if(e.code!=='ENOENT') throw e; }
  if (!process.env.X_AUTH_TOKEN) { process.stdout.write(JSON.stringify({error:'missing_auth_token'})); return; }
  const request=JSON.parse(fs.readFileSync(0,'utf8'));
  if (!/^[A-Za-z0-9_]{1,15}$/.test(request.handle || '') || typeof request.query!=='string' || request.query.length>1024 ||
      (request.cursor != null && (typeof request.cursor!=='string' || request.cursor.length>10000)))
    throw new Error('Invalid request');
  // Avoid exposing provider diagnostics, which can contain headers or response bodies.
  console.log=console.warn=console.error=()=>{};
  let Emusks;
  const timer=setTimeout(()=>{process.stdout.write(JSON.stringify({error:'timeout'}));process.exit(1);},60000);
  try {
    Emusks=(await import('emusks')).default;
    const client=new Emusks();
    await client.login({auth_token:process.env.X_AUTH_TOKEN,client:'web'});
    const account=await client.users.getByUsername(request.handle);
    if (account?.protected || account?.username?.toLowerCase()!==request.handle.toLowerCase())
      throw new Error('Invalid public account');
    const page=await client.search.latest(request.query,{count:20,cursor:request.cursor || undefined});
    process.stdout.write(JSON.stringify(normalizePage(account,page)));
  } catch(error) {
    process.stdout.write(JSON.stringify({error:errorCode(error)}));
  } finally {
    clearTimeout(timer);
    if(Emusks) await Emusks.close();
  }
}

if (process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  main().catch(()=>{process.stdout.write(JSON.stringify({error:'request_failed'}));process.exitCode=1;});
}
