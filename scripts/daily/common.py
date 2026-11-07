"""Shared paths and helpers for the daily update job (scripts/daily/*)."""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

EVD = ROOT / "evidence"
STATE = ROOT / "data/state.json"
NEW_LOG = ROOT / "data/new_statements.jsonl"   # one line per statement the daily job added
SNAPSHOT_DATE = "2026-11-05"                   # the original collection ran up to this date


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today():
    return datetime.now(timezone.utc).date().isoformat()


def load_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save_json(path, obj, indent=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=indent))


def load_state():
    st = load_json(STATE, {})
    st.setdefault("x", {"since": f"{SNAPSHOT_DATE}T00:00:00Z"})
    st.setdefault("crec", {"since": SNAPSHOT_DATE})
    st.setdefault("chrg", {"since": SNAPSHOT_DATE})
    st.setdefault("web", {"since": f"{SNAPSHOT_DATE}T00:00:00Z", "seen": []})
    return st


def save_state(st):
    st["web"]["seen"] = st["web"]["seen"][-20000:]
    save_json(STATE, st, indent=1)


def roster():
    return json.loads((ROOT / "data/roster.json").read_text())


def append_statements(pid, new):
    """Add statements to evidence/{pid}.json with the next free sids. Never renumbers existing ones.
    Skips duplicates of existing statements (same fuzzy rule as phase2_assemble.dedupe). Returns added."""
    from phase2_assemble import dedupe
    f = EVD / f"{pid}.json"
    ev = json.loads(f.read_text())
    old = ev["statements"]
    merged = dedupe(old + new)              # dedupe keeps the first copy, so old statements win
    known = {(s["url"], s["text"]) for s in old}
    added = [s for s in merged if (s["url"], s["text"]) not in known]
    if not added:
        return []
    nxt = max((int(s["sid"][1:]) for s in old), default=0) + 1
    for i, s in enumerate(added):
        s["sid"] = f"s{nxt + i}"
        s["added"] = today()
    ev["statements"] = [s for s in merged if (s["url"], s["text"]) in known] + added
    f.write_text(json.dumps(ev, indent=1))
    with NEW_LOG.open("a") as fh:
        for s in added:
            fh.write(json.dumps({"id": pid, "sid": s["sid"], "added": s["added"], "origin": s["origin"], "url": s["url"]}) + "\n")
    return added


def split_sentences(text):
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z\"“])", text) if x.strip()]
