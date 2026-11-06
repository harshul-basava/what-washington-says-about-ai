"""Apply decisions exported from site/review.html, then rebuild scores and site data.

  uv run python scripts/phase4_apply_review.py ~/Downloads/review_decisions.json

Decisions are merged into data/human_review.json (key "id|dimension"). A later export of the
same item replaces the earlier one. `combine` applies them on every run, so they survive rescoring.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(path):
    new = json.loads(Path(path).expanduser().read_text())["decisions"]
    f = ROOT / "data/human_review.json"
    hr = json.loads(f.read_text()) if f.exists() else {}
    for d in new:
        hr[f"{d['id']}|{d['dimension']}"] = {k: d.get(k) for k in ("verdict", "score", "note", "at")}
    f.write_text(json.dumps(hr, indent=1))
    changed = sum(1 for d in hr.values() if d["verdict"] == "change")
    print(f"{len(hr)} decisions stored ({changed} score changes)")
    for cmd in (["scripts/phase3_score.py", "combine"], ["scripts/phase5_build_site.py"], ["scripts/phase4_review_ui.py"]):
        subprocess.run(["uv", "run", "python", *cmd], cwd=ROOT, check=True)


if __name__ == "__main__":
    main(sys.argv[1])
