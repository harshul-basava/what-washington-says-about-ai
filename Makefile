# What Washington Says About AI — pipeline
# `make refresh` re-runs evidence + scoring + site. Paid steps go through llm.py (budget-capped).
# Web research and X collection skip people already done; to re-research someone, delete
# data/raw/web/<id>.json and/or data/raw/x_emusks/<id>.json first (or `make clean-evidence` for everyone).

PY = uv run python

.PHONY: roster handles x x-free web assemble score site refresh clean-evidence serve daily daily-dry federal federal-dry federal-x federal-x-plan history calibrate policies-plan policies-label policies-build test

roster:            ## Phase 1: current members + called 2026 races
	$(PY) scripts/phase1_roster.py
	$(PY) scripts/phase1_handles_elect.py
	$(PY) scripts/phase1_roster.py
	$(PY) scripts/phase1_next_congress.py

handles:           ## pick primary handles from post authors, write handle_review.csv (run after x)
	$(PY) scripts/phase1_handles_finalize.py

x:                 ## Phase 2: X posts via paid full-archive API ($0.005/post, capped 500/person)
	$(PY) scripts/x_paid.py data/x_people_prelim.json

x-free:            ## alternative: X posts via emusks (free, slow: ~1 request / 20s)
	node scripts/x_emusks.mjs data/x_people_prelim.json

web:               ## Phase 2: web research + quote verification (~$0.12/person)
	$(PY) scripts/phase2_web.py --workers 6

assemble:          ## Phase 2: merge CeSIA + X + web into evidence/
	$(PY) scripts/phase2_assemble.py

score:             ## Phase 3 (rubric v3): label every statement with two judges, then score with the fixed formula
	$(PY) scripts/phase3_label.py submit
	$(PY) scripts/phase3_label.py collect
	$(PY) scripts/phase3_label.py combine

daily:             ## Daily update: collect new statements, cascade-label, re-score, log changes, rebuild site data
	$(PY) scripts/daily/run.py

daily-dry:         ## Plan the daily update without paid calls or writes
	$(PY) scripts/daily/run.py --dry-run

federal:           ## Collect, assess and build federal policy updates only
	$(PY) scripts/daily/run.py --sources federal $(FEDERAL_ARGS)

federal-dry:       ## Plan federal collection and judgments without network calls or writes
	$(PY) scripts/daily/run.py --sources federal --dry-run

federal-x-plan:    ## Plan emusks X search without authentication or network calls
	$(PY) scripts/federal_x.py plan $(X_ARGS)

federal-x:         ## Collect federal X posts with resumable emusks searches
	$(PY) scripts/federal_x.py collect $(X_ARGS)

history:           ## Rebuild the score history (monthly backfill from labels + daily snapshots)
	$(PY) scripts/daily/history.py backfill
	$(PY) scripts/daily/history.py build

calibrate:         ## One-time: pick the cascade confidence threshold (~$3-5)
	$(PY) scripts/daily/calibrate.py

site:              ## Phase 5: offline build of site/data from tracked research and reference inputs
	$(PY) scripts/phase5_build_site.py

refresh: roster x handles web assemble score site

clean-evidence:    ## force full re-research on next refresh (costs money)
	rm -rf data/raw/web data/raw/x_emusks data/raw/scores

serve:
	cd site && python3 -m http.server 8765

policies-plan:     ## offline coverage and cost estimate for new policy judgments
	$(PY) scripts/phase3_policies.py plan

policies-label:    ## paid, resumable confidence judgments; default additional budget $5
	$(PY) scripts/phase3_policies.py label $(POLICY_ARGS)

policies-build:    ## offline rebuild from tracked evidence and judgments
	$(PY) scripts/phase3_policies.py build

test:
	$(PY) -m unittest discover -s tests -v
	node --test tests/*.test.cjs
