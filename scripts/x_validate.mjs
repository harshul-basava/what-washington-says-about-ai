// Validate X handles via emusks profile lookup (free). Caches results in data/raw/x_profiles.json.
// Usage: node scripts/x_validate.mjs  (reads candidate_handles from data/roster.json)
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import Emusks from "emusks";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const CACHE = path.join(ROOT, "data/raw/x_profiles.json");
const env = Object.fromEntries(fs.readFileSync(path.join(ROOT, ".env"), "utf8").split("\n")
  .filter((l) => l.includes("=") && !l.startsWith("#")).map((l) => [l.slice(0, l.indexOf("=")), l.slice(l.indexOf("=") + 1).trim()]));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const withTimeout = (pr, ms = 30_000) => Promise.race([pr, new Promise((_, rej) => setTimeout(() => rej(new Error("timeout")), ms))]);

const cache = fs.existsSync(CACHE) ? JSON.parse(fs.readFileSync(CACHE, "utf8")) : {};
const roster = JSON.parse(fs.readFileSync(path.join(ROOT, "data/roster.json"), "utf8"));
const handles = [...new Set(roster.flatMap((p) => p.candidate_handles).map((h) => h.toLowerCase()))].filter((h) => !(h in cache));
console.log(`to check: ${handles.length}`);

const client = new Emusks();
await client.login(env.X_AUTH_TOKEN);
let i = 0;
for (const h of handles) {
  i++;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const u = await withTimeout(client.users.getByUsername(h));
      cache[h] = { exists: true, id: u.id, username: u.username, name: u.name, posts: u.stats?.posts,
        followers: u.stats?.followers?.count, protected: u.protected ?? null, description: u.description ?? u.bio ?? null,
        created_at: u.created_at ?? null };
      break;
    } catch (e) {
      const msg = String(e?.message || e);
      if (/"data":\{\}|not found|suspended|User has been/i.test(msg)) { cache[h] = { exists: false }; break; }
      if (/timeout/.test(msg) && attempt < 2) { await sleep(10_000); continue; }
      if (/429|rate/i.test(msg)) { console.error("rate limited; sleeping 15m"); await sleep(15 * 60_000); continue; }
      cache[h] = { exists: null, error: msg.slice(0, 200) }; break;
    }
  }
  if (i % 25 === 0) { fs.writeFileSync(CACHE, JSON.stringify(cache, null, 1)); console.log(`${i}/${handles.length}`); }
  await sleep(6500); // ~138 / 15 min, under the documented 150
}
fs.writeFileSync(CACHE, JSON.stringify(cache, null, 1));
console.log("done", Object.values(cache).filter((v) => v.exists).length, "exist of", Object.keys(cache).length);
