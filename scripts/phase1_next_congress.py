"""Phase 1 (add-on): who will sit in the 120th Congress (January 2027)?

For each current member:
  continuing  senator whose term runs past Jan 2027, or a member who won a 2026 race (House or Senate)
  departing   their race was called and someone else won it (lost, retired, or ran for another office and lost)
  pending     their seat's race isn't called yet
Members-elect are "arriving". Writes data/next_congress.json {id: {status, chamber in the 120th}}.
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase1_roster import NICK, house_results, norm_name, senate_results  # noqa: E402

RAW = ROOT / "data/raw"


def main():
    legis = {m["id"]["bioguide"]: m for m in json.loads((RAW / "legislators-current.json").read_text())}
    roster = json.loads((ROOT / "data/roster.json").read_text())
    house = house_results()
    senate = senate_results()
    winners = [(n, "house") for ws in house.values() for n, _ in ws] + [(n, "senate") for _, _, ws in senate for n, _ in ws]

    def won(m):
        nm = m["name"]
        pt = norm_name(nm.get("official_full") or f"{nm['first']} {nm['last']}")
        firsts = {f for x in (nm.get("first"), nm.get("nickname"), nm.get("middle")) if x for f in norm_name(x)} | set(pt[:-1])
        firsts |= {NICK.get(f, f) for f in firsts}
        for w, ch in winners:
            t = norm_name(w)
            if not t:
                continue
            t = [NICK.get(a, a) for a in t[:-1]] + t[-1:]
            if t[-1] in pt and any(a.startswith(b) or b.startswith(a) for a in t[:-1] for b in firsts if len(a) > 1 and len(b) > 1):
                return ch
        return None

    out, nxt_ch = {}, {}
    for p in roster:
        if p["status"] == "member_elect":
            out[p["id"]] = "arriving"
            continue
        m = legis[p["id"]]
        t = m["terms"][-1]
        ch = won(m)
        if ch:
            out[p["id"]] = "continuing"
            nxt_ch[p["id"]] = ch
        elif t["type"] == "sen":
            if t["end"] > "2027-01-04":
                out[p["id"]] = "continuing"
            else:
                races = [ws for st, _, ws in senate if st == t["state"]]
                out[p["id"]] = "departing" if races and all(races) else "pending"
        else:
            dist = "0" if t.get("district") in (0, None) else str(t["district"])
            ws = house.get((t["state"], dist))
            if ws is None:
                out[p["id"]] = "pending"  # no 2026 result row (delegates are handled the same way)
            else:
                out[p["id"]] = "departing" if ws else "pending"
    res = {k: {"status": v, "chamber": nxt_ch.get(k) or next(p["chamber"] for p in roster if p["id"] == k)} for k, v in out.items()}
    (ROOT / "data/next_congress.json").write_text(json.dumps(res, indent=1))
    c = Counter(out.values())
    by = Counter((legis[k]["terms"][-1]["type"], v) for k, v in out.items() if k in legis)
    print(c, by)
    print("120th so far:", Counter(r["chamber"] for r in res.values() if r["status"] in ("continuing", "arriving")))
    print("moving chambers:", [p["name"] for p in roster if res[p["id"]]["chamber"] != p["chamber"]])


if __name__ == "__main__":
    main()
