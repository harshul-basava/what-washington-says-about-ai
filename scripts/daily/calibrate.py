"""Calibrate the cascade's confidence threshold against the existing two-judge labels (one-time, about $3-5).

Takes a random sample of members' statements that already have Sonnet and GPT labels, runs DeepSeek 3x and
GPT-6.1 Sol on all of them, then simulates the cascade for several thresholds. For each threshold it reports
how often the cascade's labels match the original judges, compared with how often the two original judges
match each other, plus the share of labels that escalate (which drives cost).

Writes review/cascade_calibration.md. Usage: python scripts/daily/calibrate.py [--members 40] [--per 15] [--seed 7]
"""
import argparse
import json
import random
from concurrent.futures import ThreadPoolExecutor

from common import ROOT
import label as L
from phase3_label import DIMS

THRESHOLDS = [3.0, 3.5, 4.0, 4.5, 5.0]


def agree(x, y):
    """Same decision on one (statement, question): both unlabeled, or the same level."""
    return x == y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--members", type=int, default=40)
    ap.add_argument("--per", type=int, default=15)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    base = json.loads((ROOT / "data/labels.json").read_text())
    pids = rnd.sample(sorted(p for p in base if len(base[p]) >= 5), a.members)
    jobs = []
    for pid in pids:
        ev = json.loads((ROOT / "evidence" / f"{pid}.json").read_text())
        labeled = [s for s in ev["statements"] if s["sid"] in base[pid]]
        jobs.append((pid, ev["name"], rnd.sample(labeled, min(a.per, len(labeled)))))

    def one(job):
        pid, name, sample = job
        runs = L.deepseek_runs(name, sample, tag="calibrate_ds")
        sol = L.independent(L.SOL, name, sample, "calibrate_sol")
        print(pid, len(sample), flush=True)
        return [{"pid": pid, "sid": s["sid"], "runs": [(r[0].get(s["sid"], {}), r[1].get(s["sid"], {})) for r in runs],
                 "sol": sol.get(s["sid"], {}), "sonnet": base[pid][s["sid"]].get("sonnet", {}), "gpt": base[pid][s["sid"]].get("gpt", {})}
                for s in sample]
    rows = []   # (sid-level records)
    with ThreadPoolExecutor(a.workers) as ex:
        for r in ex.map(one, jobs):
            rows += r
    (ROOT / "review/cascade_calibration_raw.json").write_text(json.dumps(rows))

    def judges_match():
        n = m = 0
        for r in rows:
            for k in DIMS:
                n += 1
                m += agree(r["sonnet"].get(k), r["gpt"].get(k))
        return m / n

    lines = ["# Cascade calibration", "",
             f"Sample: {len(rows)} statements from {len(pids)} members (seed {a.seed}), each already labeled by Sonnet 5.5 and GPT-6.1 Sol.",
             f"Baseline: the two original judges give the same decision on {judges_match():.1%} of (statement, question) pairs.", "",
             "| Confidence threshold | Escalated labels | Cascade A vs Sonnet | Cascade B vs GPT | Mean |", "|---|---|---|---|---|"]
    for t in THRESHOLDS:
        L.CONF_MIN = t
        esc = tot = ma = mb = n = 0
        for r in rows:
            runs = [({r["sid"]: x[0]}, {r["sid"]: x[1]}, {}) for x in r["runs"]]
            maj, _, e = L.decide(r["sid"], runs, {})
            av, bv = dict(maj), dict(maj)
            for k in e:
                bv.pop(k, None)
                if r["sol"].get(k) is not None:
                    bv[k] = r["sol"][k]
            esc += len(e)
            tot += sum(1 for k in DIMS if any(x[0].get(k) is not None for x in r["runs"]))
            for k in DIMS:
                n += 1
                ma += agree(av.get(k), r["sonnet"].get(k))
                mb += agree(bv.get(k), r["gpt"].get(k))
        lines.append(f"| {t} | {esc / max(tot, 1):.0%} | {ma / n:.1%} | {mb / n:.1%} | {(ma + mb) / 2 / n:.1%} |")
    lines += ["", "Pick the cheapest threshold whose mean agreement is at least the baseline, and set `CONF_MIN` in "
              "`scripts/daily/label.py`. Astra tie-breaks are not simulated here (they are rare and only move labels toward a third opinion)."]
    (ROOT / "review/cascade_calibration.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
