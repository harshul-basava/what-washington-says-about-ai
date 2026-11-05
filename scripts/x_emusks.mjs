// Free X collection via emusks (logged-in web search, "Latest" tab).
// Usage: node scripts/x_emusks.mjs <people.json>   where people.json = [{id, handles:[...]}]
//        node scripts/x_emusks.mjs --one <id> <handle1,handle2>
// Writes data/raw/x_emusks/{id}.json. Skips people already done. Never logs the token.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import Emusks from "emusks";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "data/raw/x_emusks");
fs.mkdirSync(OUT, { recursive: true });

const env = Object.fromEntries(
  fs.readFileSync(path.join(ROOT, ".env"), "utf8").split("\n")
    .filter((l) => l.includes("=") && !l.startsWith("#"))
    .map((l) => [l.slice(0, l.indexOf("=")), l.slice(l.indexOf("=") + 1).trim()]),
);

const KEYWORDS = '(AI OR "artificial intelligence" OR AGI OR superintelligence OR OpenAI OR Anthropic OR ChatGPT OR deepfake OR "machine learning" OR chatbot)';
const SINCE = "2023-01-01";
const MIN_GAP_MS = 20_000; // ~45 req / 15 min, under the documented 50
const MAX_PAGES = 40; // safety cap per person (~800 posts)

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let last = 0;
async function throttled(fn) {
  const wait = last + MIN_GAP_MS - Date.now();
  if (wait > 0) await sleep(wait);
  for (let attempt = 0; ; attempt++) {
    last = Date.now();
    try {
      return await fn();
    } catch (e) {
      const msg = String(e?.message || e);
      if (attempt < 4 && /429|rate|limit|88/i.test(msg)) {
        console.error(`  rate limited, sleeping 15m (attempt ${attempt + 1})`);
        await sleep(15 * 60_000);
        continue;
      }
      throw e;
    }
  }
}

function slim(t) {
  return {
    id: t.id, text: t.text ?? t.full_text, created_at: t.created_at ?? t.createdAt,
    author: t.user?.username ?? t.author?.username ?? t.user?.screen_name,
    lang: t.lang, is_reply: Boolean(t.in_reply_to_status_id ?? t.inReplyToStatusId ?? t.replyTo),
    quoted: t.quoting?.text ?? null,
  };
}

// X web search stops paginating early on long result sets. So we walk backwards in time:
// paginate until the cursor dries up, then restart with until:<oldest day seen + 1>.
// Stop when a round adds nothing new or we pass SINCE.
async function collect(client, person) {
  const from = person.handles.map((h) => `from:${h.replace(/^@/, "")}`).join(" OR ");
  const base = `(${from}) ${KEYWORDS} since:${SINCE} -filter:retweets`;
  const posts = new Map();
  let until = null, pages = 0;
  for (let round = 0; round < 30 && pages < MAX_PAGES; round++) {
    const q = until ? `${base} until:${until}` : base;
    let cursor, newThisRound = 0, empties = 0;
    while (pages < MAX_PAGES) {
      const res = await throttled(() => client.search.latest(q, { count: 20, cursor }));
      pages++;
      const tweets = res.tweets || [];
      let added = 0;
      for (const t of tweets) if (t?.id && !posts.has(t.id)) { posts.set(t.id, t); added++; }
      newThisRound += added;
      empties = added === 0 ? empties + 1 : 0;
      if (!res.nextCursor || empties >= 2) break;
      cursor = res.nextCursor;
    }
    if (newThisRound === 0) break;
    const oldest = Math.min(...[...posts.values()].map((t) => new Date(t.created_at).getTime()));
    const next = new Date(oldest + 86_400_000).toISOString().slice(0, 10); // until: is exclusive
    if (next <= SINCE || next === until) break;
    until = next;
  }
  return { query: base, pages, raw: [...posts.values()] };
}

const args = process.argv.slice(2);
const people = args[0] === "--one"
  ? [{ id: args[1], handles: args[2].split(",") }]
  : JSON.parse(fs.readFileSync(args[0], "utf8"));

const client = new Emusks();
await client.login(env.X_AUTH_TOKEN);

for (const p of people) {
  const f = path.join(OUT, `${p.id}.json`);
  if (fs.existsSync(f)) continue;
  try {
    const { query, pages, raw } = await collect(client, p);
    const posts = raw.map(slim).map((s) => ({ ...s, url: `https://x.com/${s.author}/status/${s.id}` }));
    fs.writeFileSync(f, JSON.stringify({ id: p.id, handles: p.handles, query, pages, n: posts.length,
      collected_at: new Date().toISOString(), posts, raw }, null, 1));
    const dates = posts.map((x) => new Date(x.created_at)).filter((d) => !isNaN(d)).sort((a, b) => a - b);
    console.log(`${p.id} n=${posts.length} pages=${pages} range=${dates[0]?.toISOString().slice(0, 10)}..${dates.at(-1)?.toISOString().slice(0, 10)}`);
  } catch (e) {
    console.error(`${p.id} FAILED: ${String(e?.message || e).slice(0, 300)}`);
  }
}
