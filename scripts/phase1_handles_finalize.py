"""Phase 1 (finalize, after X collection): pick X handles per person.

Each collected post includes its author's profile, so the handles are checked against the
returned authors rather than a separate lookup pass:
- valid handles = authors seen in that person's results whose profile name contains the person's
  last name (or whose handle does). Other authors go to review and their posts are dropped.
- primary handle = valid author with the most posts on their profile; when no AI posts were
  found, the first candidate (the official account from congress-legislators) is shown instead.
- handle_review.csv lists: no handle, name mismatches, and member-elect handles found by web search.
Writes data/handles.json (primary), data/x_people.json (validated handles), handle_review.csv.
"""
import csv
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def toks(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return set(re.sub(r"[^a-z ]", " ", s).split())


def main():
    roster = json.loads((ROOT / "data/roster.json").read_text())
    prof_f = ROOT / "data/raw/x_profiles.json"
    prof = json.loads(prof_f.read_text()) if prof_f.exists() else {}
    primary, people, review = {}, [], []
    for p in roster:
        name_toks = [t for t in toks(p["name"]) if len(t) > 2 and t not in {"jr", "iii"}]
        last = name_toks[-1] if name_toks else ""
        authors = {}
        f = ROOT / "data/raw/x_emusks" / f"{p['id']}.json"
        if f.exists():
            for t in json.loads(f.read_text()).get("raw", []):
                u = t.get("user") or {}
                if u.get("username"):
                    authors[u["username"].lower()] = u
        valid, reasons = [], []
        for h, u in authors.items():
            if last and (last in toks(u.get("name")) or last in h):
                valid.append(u)
            else:
                reasons.append(f"@{u['username']} profile name '{u.get('name')}' lacks '{last}' (posts dropped)")
        valid.sort(key=lambda u: -((u.get("stats") or {}).get("posts") or 0))
        if valid:
            primary[p["id"]] = valid[0]["username"]
        elif p["candidate_handles"]:
            # no AI posts found: show the first candidate if a lookup didn't rule it out
            h = p["candidate_handles"][0]
            if prof.get(h.lower(), {}).get("exists", True):
                primary[p["id"]] = h
        if not p["candidate_handles"]:
            reasons.append("no handle found")
        if p["status"] == "member_elect" and p["candidate_handles"]:
            reasons.append("member-elect handle found by web search")
        people.append({"id": p["id"], "handles": [u["username"] for u in valid]})
        if reasons:
            review.append({"id": p["id"], "name": p["name"], "state": p["state"], "status": p["status"],
                           "candidate_handles": " ".join(p["candidate_handles"]),
                           "validated_handles": " ".join(u["username"] for u in valid),
                           "primary": primary.get(p["id"], ""), "reasons": "; ".join(reasons), "corrected_handles": ""})
    (ROOT / "data/handles.json").write_text(json.dumps(primary, indent=1))
    (ROOT / "data/x_people.json").write_text(json.dumps(people, indent=1))
    with open(ROOT / "handle_review.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "name", "state", "status", "candidate_handles", "validated_handles",
                                           "primary", "reasons", "corrected_handles"])
        w.writeheader()
        w.writerows(review)
    print(f"people with AI posts from a validated handle: {sum(bool(p['handles']) for p in people)}/{len(roster)}; "
          f"review rows: {len(review)}")


if __name__ == "__main__":
    main()
