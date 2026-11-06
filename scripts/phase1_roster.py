"""Phase 1: build data/roster.json (current members + 2026 members-elect).

Sources (all free, in data/raw/): unitedstates congress-legislators (current + social media),
Wikidata X handles (P2002 keyed by bioguide P1157), Voteview DW-NOMINATE (HS119), and
Wikipedia 2026 House/Senate election pages (winners marked {{aye}}).
Member-elect X handles are found in phase1_handles_elect.py; handle validation in x_validate.mjs.
"""
import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"


def norm_name(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", s)
    return re.sub(r"[^a-z ]", "", s).split()


NICK = {"jim": "james", "jimmy": "james", "tom": "thomas", "nick": "nicholas", "mike": "michael",
        "bill": "william", "bob": "robert", "rob": "robert", "dick": "richard", "rick": "richard",
        "chuck": "charles", "chris": "christopher", "dan": "daniel", "dave": "david", "joe": "joseph",
        "ted": "edward", "ed": "edward", "tim": "timothy", "steve": "steven", "andy": "andrew",
        "tony": "anthony", "greg": "gregory", "hal": "harold", "pat": "patrick", "ron": "ronald",
        "don": "donald", "jerry": "gerald", "ben": "benjamin", "matt": "matthew", "jeff": "jeffrey",
        "sam": "samuel", "bobby": "robert", "johnny": "john", "jack": "john", "liz": "elizabeth",
        "kate": "katherine", "beth": "elizabeth", "pete": "peter", "zach": "zachary", "abe": "abraham", "lou": "luis"}


def last_name(s):
    t = norm_name(s)
    return t[-1] if t else ""


STATES = {"Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
          "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
          "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
          "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
          "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
          "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
          "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
          "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
          "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
          "Wisconsin": "WI", "Wyoming": "WY"}

WIN = re.compile(r"\{\{\s*aye\s*\}\}\s*'''\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'''\s*\(([^)]+)\)", re.I)
WIN_PLAIN = re.compile(r"\{\{\s*aye\s*\}\}\s*'''([^'\[]+)'''\s*\(([^)]+)\)", re.I)


def winners(block):
    out = [(m.group(2) or m.group(1), m.group(3)) for m in WIN.finditer(block)]
    out += [(m.group(1), m.group(2)) for m in WIN_PLAIN.finditer(block)]
    return [(re.sub(r"\s*\(.*\)$", "", n).strip(), p) for n, p in out]


def house_results():
    w = json.loads((RAW / "wiki_2026_United_States_House_of_Representatives_elections.json").read_text())["parse"]["wikitext"]
    w = w[w.find("==Alabama=="):]
    res = {}
    for b in re.split(r"\n(?=!(?:rowspan=\d+ ?\|)?\s*\{\{ushr\|)", w)[1:]:
        m = re.match(r"!(?:rowspan=\d+ ?\|)?\s*\{\{ushr\|(\w+)\|(\w+)", b)
        b = re.split(r"\n\|\}|\n==", b)[0]
        st, dist = m.group(1).upper(), m.group(2)
        dist = "0" if dist.upper() in ("AL", "AT-LARGE") else dist
        res[(st, dist)] = winners(b)
    return res


def senate_results():
    w = json.loads((RAW / "wiki_2026_United_States_Senate_elections.json").read_text())["parse"]["wikitext"]
    secs = []
    for head in ("Special elections during the preceding Congress", "Elections leading to the next Congress"):
        i = w.find(head)
        seg = w[i:]
        secs.append(seg[: seg.find("\n==", 10)])
    res = []
    for b in re.split(r"\n\|-\n", "\n|-\n".join(secs)):
        m = re.search(r"^!\s*\[\[2026 United States Senate (?:special )?election in ([^|\]]+)\|", b, re.M)
        if m and m.group(1) in STATES:
            res.append((STATES[m.group(1)], "special" in b[:200], winners(b)))
    return res


def main():
    cur = json.loads((RAW / "legislators-current.json").read_text())
    soc = {s["id"]["bioguide"]: s.get("social", {}) for s in json.loads((RAW / "legislators-social-media.json").read_text())}
    wd = defaultdict(set)
    for r in json.loads((RAW / "wikidata_x.json").read_text())["results"]["bindings"]:
        if "end" not in r:
            wd[r["bio"]["value"]].add(r["h"]["value"])
    nom = {}
    with open(RAW / "voteview_HS119.csv") as f:
        for r in csv.DictReader(f):
            if r["bioguide_id"] and r["nominate_dim1"]:
                nom[r["bioguide_id"]] = float(r["nominate_dim1"])

    roster = []
    by_state_last = defaultdict(list)
    for m in cur:
        t = m["terms"][-1]
        bio = m["id"]["bioguide"]
        handles = []
        if soc.get(bio, {}).get("twitter"):
            handles.append(soc[bio]["twitter"])
        for h in sorted(wd.get(bio, [])):
            if h.lower() not in {x.lower() for x in handles}:
                handles.append(h)
        for h in json.loads((RAW / "elect_handles.json").read_text()).get(bio, []) if (RAW / "elect_handles.json").exists() else []:
            if h["handle"].lower() not in {x.lower() for x in handles}:
                handles.append(h["handle"])
        name = m["name"].get("official_full") or f"{m['name']['first']} {m['name']['last']}"
        p = {
            "id": bio, "name": name, "chamber": "senate" if t["type"] == "sen" else "house",
            "state": t["state"], "district": t.get("district"), "party": t.get("party"),
            "status": "current", "race_called": None, "candidate_handles": handles,
            "ideology_dw1": nom.get(bio), "wikipedia": m["id"].get("wikipedia"),
            "_firsts": {x.lower() for x in (m["name"].get("first"), m["name"].get("nickname"), m["name"].get("middle")) if x}
            | set(norm_name(name)[:-1]),
        }
        roster.append(p)
        by_state_last[(t["state"], last_name(m["name"]["last"]))].append(p)

    currents = [p for p in roster if p["status"] == "current"]

    def is_current(state, name):
        """Same last name AND same first name/initial (any state: covers House->Senate moves)."""
        t = norm_name(name)
        if not t:
            return False
        for p in currents:
            pt = norm_name(p["name"])
            firsts = {f for x in p["_firsts"] for f in norm_name(x)}
            firsts |= {NICK.get(f, f) for f in firsts}
            t = [NICK.get(a, a) for a in t[:-1]] + t[-1:]
            if t[-1] in pt and any(a.startswith(b) or b.startswith(a) for a in t[:-1] for b in firsts if len(a) > 1 and len(b) > 1):
                return True
        return False

    uncalled = []
    elect = []
    for (st, dist), ws in house_results().items():
        if not ws:
            uncalled.append(f"house {st}-{dist}")
            continue
        for n, party in ws:
            if not is_current(st, n):
                elect.append(("house", st, dist, n, party))
    for st, special, ws in senate_results():
        if not ws:
            uncalled.append(f"senate {st}{' special' if special else ''}")
            continue
        for n, party in ws:
            # a sitting House member winning a Senate seat is still "current"
            if not is_current(st, n):
                elect.append(("senate", st, None, n, party))

    eh_file = RAW / "elect_handles.json"
    eh = json.loads(eh_file.read_text()) if eh_file.exists() else {}
    for ch, st, dist, n, party in elect:
        tid = "E_" + re.sub(r"[^A-Za-z]", "", "".join(norm_name(n))).upper()[:16] + f"_{st}"
        tid = tid  # noqa
        roster.append({"id": tid, "name": n, "chamber": ch, "state": st,
                       "district": int(dist) if dist and dist.isdigit() else dist, "party": party,
                       "status": "member_elect", "race_called": True,
                       "candidate_handles": list(dict.fromkeys(h["handle"] for h in eh.get(tid, []))),
                       "ideology_dw1": None, "wikipedia": n})
    review = [(e[1], e[2], e[3], [p["name"] for p in currents if p["state"] == e[1] and last_name(e[3]) in norm_name(p["name"])])
              for e in elect]
    review = [r for r in review if r[3]]
    print("member-elect sharing a last name with a same-state current member (check):", review)
    for p in roster:
        p.pop("_firsts", None)
    (ROOT / "data/roster.json").write_text(json.dumps(roster, indent=1))
    (ROOT / "data/uncalled_races.json").write_text(json.dumps(sorted(uncalled), indent=1))
    print(f"current={sum(p['status']=='current' for p in roster)} member_elect={len(elect)} uncalled={len(uncalled)}")
    print("with >=1 candidate handle:", sum(bool(p["candidate_handles"]) for p in roster))


if __name__ == "__main__":
    main()
