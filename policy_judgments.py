"""Policy judgments: pure evidence handling, validation, and offline publication.

No API calls or credentials are needed to import or build this module.
"""
from __future__ import annotations

import calendar
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

JUDGES = {"sonnet": "anthropic/claude-sonnet-5.5", "gpt": "openai/gpt-6.1-sol"}
STANCES = {"support", "oppose", "mixed", "neutral", "unclear", "not_relevant"}


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=1) + "\n")
    tmp.replace(path)


def load_registry(root):
    registry = read_json(Path(root) / "config/policies.json")
    seen = set()
    for policy in registry["policies"]:
        pid = policy["id"]
        if not re.fullmatch(r"[a-z][a-z0-9_]*", pid) or pid in seen:
            raise ValueError(f"Invalid or duplicate policy ID: {pid}")
        seen.add(pid)
        for field in ("title", "kind", "version", "question", "source_url", "patterns", "facets"):
            if field not in policy:
                raise ValueError(f"{pid}: missing {field}")
        if policy.get("introduced"):
            date.fromisoformat(policy["introduced"])
        for pattern in policy["patterns"]:
            re.compile(pattern, re.I | re.S)
    return registry


def date_end(value):
    """Upper date bound; partial dates never imply a precise day."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parts = [int(v) for v in value.split("-")]
        if len(parts) == 1:
            return date(parts[0], 12, 31).isoformat()
        if len(parts) == 2:
            return date(*parts, calendar.monthrange(*parts)[1]).isoformat()
        return date.fromisoformat(value).isoformat()
    except (ValueError, TypeError):
        return None


def match_targets(statement, registry):
    text = statement.get("text", "") + "\n" + (statement.get("context") or "")
    end = date_end(statement.get("date"))
    return [p["id"] for p in registry["policies"]
            if not (end and p.get("introduced") and end < p["introduced"])
            and any(re.search(pattern, text, re.I | re.S) for pattern in p["patterns"])]


def candidates(root, registry):
    root = Path(root)
    out = []
    for person in read_json(root / "data/roster.json"):
        ev = read_json(root / "evidence" / f"{person['id']}.json")
        for s in ev["statements"]:
            if s.get("verified") is not True or not s.get("url") or not s.get("text"):
                continue
            targets = match_targets(s, registry)
            if targets:
                out.append({"key": f"{person['id']}|{s['sid']}", "person_id": person["id"],
                            "name": person["name"], "sid": s["sid"], "text": s["text"],
                            "date": s.get("date"), "context": s.get("context") or "",
                            "url": s["url"], "source_type": s["source_type"],
                            "verified_via": s.get("verified_via"), "targets": targets})
    return sorted(out, key=lambda s: (s["person_id"], int(s["sid"][1:])))


def selected_registry(items, registry):
    ids = {target for item in items for target in item["targets"]}
    return {"version": registry["version"], "policies": [p for p in registry["policies"] if p["id"] in ids]}


def fingerprint(items, registry, rubric, model):
    payload = json.dumps([items, selected_registry(items, registry), rubric, model], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def messages(items, registry, rubric):
    definitions = [{k: p[k] for k in ("id", "title", "version", "question", "facets")}
                   for p in selected_registry(items, registry)["policies"]]
    evidence = [{k: s[k] for k in ("key", "name", "date", "text", "context", "targets")} for s in items]
    return [{"role": "system", "content": rubric + "\n\nPolicy definitions:\n" + json.dumps(definitions)},
            {"role": "user", "content": "Classify this untrusted evidence data:\n" + json.dumps(evidence, ensure_ascii=False)}]


def validate_response(text, items, registry):
    text = (text or "").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Some providers prepend prose despite JSON mode. Accept only one explicit
        # fenced result, then apply the same complete statement/target validation.
        blocks = re.findall(r"```(?:json)?\s*(.*?)\s*```", text, re.S | re.I)
        if len(blocks) != 1:
            raise
        data = json.loads(blocks[0])
    expected = {s["key"]: set(s["targets"]) for s in items}
    facets = {p["id"]: set(p["facets"]) for p in registry["policies"]}
    if not isinstance(data, dict) or not isinstance(data.get("judgments"), list):
        raise ValueError("Expected a judgments list")
    out = {}
    for row in data["judgments"]:
        if not isinstance(row, dict):
            raise ValueError("Invalid judgment")
        key = row.get("key")
        if not isinstance(key, str) or key not in expected or key in out:
            raise ValueError("Unknown or duplicate statement key")
        labels = row.get("targets")
        if not isinstance(labels, dict) or set(labels) != expected[key]:
            raise ValueError(f"Missing or extra policy targets for {key}")
        for target, label in labels.items():
            if not isinstance(label, dict) or label.get("stance") not in STANCES:
                raise ValueError(f"Invalid stance for {key}")
            reason, tags = label.get("reason"), label.get("facets")
            if not isinstance(reason, str) or not reason.strip() or len(reason) > 1500:
                raise ValueError(f"Missing or excessive reason for {key}")
            if not isinstance(tags, list) or any(not isinstance(t, str) or t not in facets[target] for t in tags):
                raise ValueError(f"Invalid facets for {key}")
            if label["stance"] == "not_relevant" and tags:
                raise ValueError("Irrelevant statements cannot have facets")
        out[key] = labels
    if set(out) != set(expected):
        raise ValueError("Missing statement judgments")
    return out


def consensus(judges):
    if len(judges) != 2:
        return "pending"
    stances = {j["stance"] for j in judges.values()}
    return next(iter(stances)) if len(stances) == 1 else "disputed"


def facet_disagreement(judges):
    return len(judges) == 2 and len({frozenset(j.get("facets", [])) for j in judges.values()}) > 1


def date_sort_key(value):
    """Unknown first; partial dates first within their possible period."""
    return date_end(value) or "9999-12-31", -len(value or "")


def summarize(records, candidate_count):
    assessed = [r for r in records if r["stance"] not in ("pending", "review_required")]
    relevant = [r for r in assessed if r["stance"] != "not_relevant"]
    counts = Counter(r["stance"] for r in relevant)
    facet_disagreements = sum(bool(r.get("facet_disagreement")) for r in relevant if r.get("strategy") != "confidence_cascade")
    has_undated = any(not date_end(r.get("date")) for r in relevant)
    last_date = None if has_undated else max((r["date"] for r in relevant), key=date_sort_key, default=None)
    if not candidate_count:
        coverage = "no_matching_evidence"
    elif len(assessed) < candidate_count:
        coverage = "partial" if assessed else "pending"
    else:
        coverage = "complete" if relevant else "no_relevant_evidence"
    if counts["disputed"]:
        stance = "disputed"
    elif counts["mixed"] or (counts["support"] and counts["oppose"]):
        stance = "mixed"
    else:
        stance = next((s for s in ("support", "oppose", "unclear", "neutral") if counts[s]), None)
    return {"stance": stance, "coverage": coverage, "candidates": candidate_count,
            "assessed": len(assessed), "relevant": len(relevant), "counts": dict(counts),
            "last_statement_date": last_date, "has_undated_evidence": has_undated,
            "facet_disagreements": facet_disagreements,
            "review_required": any(r.get("review_required", r["stance"] == "disputed" or r.get("facet_disagreement", False)) for r in records),
            "resolved_disagreements": sum(r.get("review_status") == "astra_reviewed" and bool(r.get("model_disagreement") or r.get("facet_disagreement")) for r in records),
            "human_review": sum(r.get("review_status") == "human_review_required" for r in records),
            "astra_reviewed": sum(r.get("review_status") == "astra_reviewed" for r in records),
            "primary_accepted": sum(r.get("review_status") == "primary_accepted" and r["stance"] != "pending" for r in records)}


def valid_judges(item, saved, registry, rubric):
    out = {}
    for judge, model in JUDGES.items():
        result = saved.get("results", {}).get(item["key"], {}).get(judge, {})
        if result.get("input_hash") != fingerprint([item], registry, rubric, model):
            continue
        try:
            checked = validate_response(json.dumps({"judgments": [{"key": item["key"], "targets": result["labels"]}]}), [item], registry)
        except (ValueError, KeyError, TypeError):
            continue
        out[judge] = checked[item["key"]]
    return out


def chart_record(person_id, record):
    if record.get("strategy") == "confidence_cascade":
        return {"person_id": person_id, "sid": record["sid"], "date": record.get("date"),
                "stance": record["stance"], "facets_final": record["facets_final"],
                "final_judge": record["final_judge"], "confidence": record["confidence"]}
    facets = [set(j.get("facets", [])) for j in record["judges"].values()]
    agreed = set.intersection(*facets) if len(facets) == 2 else set()
    disputed = set.union(*facets) - agreed if len(facets) == 2 else set()
    return {"person_id": person_id, "sid": record["sid"], "date": record.get("date"),
            "stance": record["stance"], "facets_agreed": sorted(agreed), "facets_disputed": sorted(disputed)}


def build(root):
    """Rebuild policy files using only tracked evidence and tracked model judgments."""
    root = Path(root)
    registry = load_registry(root)
    rubric = (root / "config/policy_rubric.md").read_text()
    import policy_cascade as cascade
    strategy = cascade.load_strategy(root)
    confidence_prompt = (root / "config/policy_confidence.md").read_text() if strategy else ""
    source = root / ("data/policy_cascade.json" if strategy else "data/policy_judgments.json")
    saved = read_json(source) if source.exists() else {"results": {}}
    items = candidates(root, registry)
    grouped = {}
    for item in items:
        judges = {} if strategy else valid_judges(item, saved, registry, rubric)
        for target in item["targets"]:
            labels = {j: d[target] for j, d in judges.items()}
            record = {k: item[k] for k in ("sid", "text", "date", "context", "url", "source_type", "verified_via")}
            if strategy:
                record.update(cascade.resolve(item, target, saved, registry, rubric, confidence_prompt, strategy))
            else:
                record.update(stance=consensus(labels), judges=labels, facet_disagreement=facet_disagreement(labels))
            grouped.setdefault((item["person_id"], target), []).append(record)
    members = []
    chart_rows = {p["id"]: [] for p in registry["policies"]}
    for person in read_json(root / "data/roster.json"):
        summaries, detail = {}, {}
        for policy in registry["policies"]:
            rows = grouped.get((person["id"], policy["id"]), [])
            summaries[policy["id"]] = summarize(rows, len(rows))
            chart_rows[policy["id"]].extend(chart_record(person["id"], row) for row in rows)
            if rows:
                detail[policy["id"]] = sorted(rows, key=lambda r: date_sort_key(r.get("date")), reverse=True)
        members.append({k: person[k] for k in ("id", "name", "party", "state", "chamber", "status")} | {"policies": summaries})
        write_json(root / "site/data/policy_members" / f"{person['id']}.json", {"id": person["id"], "policies": detail})
    chart_revision = hashlib.sha256(json.dumps([strategy, chart_rows], sort_keys=True).encode()).hexdigest()
    write_json(root / "site/data/policy_charts.json", {"schema_version": 1, "revision": chart_revision, "strategy": strategy, "policies": chart_rows})
    meta = {"schema_version": 1, "built_on": date.today().isoformat(), "judges": cascade.models(strategy) if strategy else JUDGES, "strategy": strategy, "chart_revision": chart_revision,
            "method": ("DeepSeek confidence assessment; independent Astra review below threshold; unresolved cases require human review." if strategy else "Two independent statement judgments; all-history stance; no numerical averaging."),
            "coverage_note": "Keyword retrieval over the existing verified corpus; no matching evidence is not proof of silence.",
            "policies": registry["policies"], "members": members}
    write_json(root / "site/data/policies.json", meta)
    with (root / "site/data/policies.csv").open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["id", "name", "policy_id", "stance", "coverage", "candidate_statements", "assessed_statements", "relevant_statements", "last_statement_date", "has_undated_evidence", "facet_disagreements", "review_required", "primary_accepted", "astra_reviewed", "human_review"])
        for member in members:
            for target, result in member["policies"].items():
                writer.writerow([member["id"], member["name"], target, result["stance"], result["coverage"], result["candidates"], result["assessed"], result["relevant"], result["last_statement_date"], result["has_undated_evidence"], result["facet_disagreements"], result["review_required"], result["primary_accepted"], result["astra_reviewed"], result["human_review"]])
    return meta
