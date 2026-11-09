# Federal analysis implementation plan

Authorized design: ../specs/2026-11-08-federal-analysis-design.md. Baseline: 3ae531e5f4509721524e739fa9b9bd20ceaa5ef1. Use the current checkout. The user already authorized implementation, paid backfills within existing caps, daily integration, and push.

## Tasks

1. [x] Implement `federal_analysis.py` and `federal_analysis_models.py`, with tests in `tests/test_federal_analysis.py`. Validate all statement IDs, dimension values, topic enums, regulation areas, and citations. Preserve cache progress by assessment, using evidence/context/prompt/model hashes. Test partial responses, invalidation, empty profiles, exclusions, and independent institutional attribution before implementation.
2. [x] Build offline federal scores, per-profile histories, topic counts, summaries, regulation outputs, and daily change records. Reuse `scripts.phase3_label.score_member`; test matching formula, silence display, dated-only histories, no future evidence, partial-date bounds, pending suppression, and separate cohorts.
3. [x] Add `scripts/federal_analysis.py` with plan, label, and build commands. Add daily orchestration and manual X integration. Reserve maximum request costs using live model metadata, preserve results, fail partial, and keep current lifetime/monthly caps. Test dry-run and resumed execution.
4. [x] Build `site/federal.html`, `site/federal-analysis.js`, and CSS. Link from the main site and policy profiles. Add meaningful JS tests for filtering, unknown data, history/date display, and source safety. Keep the existing Congress page and its generated data unchanged.
5. [x] Run a bounded live pilot. Inspect source/label relationships, then complete the backfill in resumable batches. Record costs and coverage. Run the daily analysis again to prove no unnecessary model calls.
6. [ ] Review, test, build, audit preservation and scope, verify desktop/mobile UI, push original master, and verify production. Update README, prompt documentation, and the coverage report with exact outcomes and limitations.

## Public data contract

`site/data/federal_analysis.json`: schema_version=1, built_on, revision, dimensions [{id,title}], regulation_areas [{id,title,group}], topics [string], methodology {text,models}, coverage {profiles,statements,labeled_statements,pending_labels,pending_regulation,pending_summaries}, organizations [{id,name,parent_id?}], members [{id,name,entity_type,organization_id,organization_ids,organization_name,n_statements,n_labeled,status,scores:{dimension:number|null},score_details:{dimension:{score,reason_a,reason_b,sids,label_count}},summary:{status,text,sids},topics:{topic:count},regulation:{status,areas:{area:{stance:0|-2|-1|1|2,sids,why}}}}]. Member status: complete, partial, no_evidence.

`site/data/federal_analysis/<id>.json`: schema_version=1, id, revision, profile (index member), statements [{sid,date,url,text,source_type,attribution,analysis:{status,a,b,topics,confidence,escalated,models}}], history [{date,scores:{dimension:number|null},n_statements,status,kind:'reconstructed'|'observed'}], changes [{date,dimension,old,new,kind,cause,sids}]. Citations always refer to this profile's statements. Source records must use `public_evidence` to avoid copied reporting context.

Revision identifies current evidence/config/cache contents; detail revision must match the index. Render missing/partial/stale states explicitly. Officials and institutions never share a denominator. History is per-profile; group charts use filtered current cohort.

## Review focus

Excluded profiles must never return via stale caches or detail URLs. New evidence must invalidate profile-wide summaries/categories. Unlabeled evidence must not become a silence zero. History must exclude unknown/future dates. Claims in summaries and regulation entries must retain valid source IDs. Daily budget exhaustion must remain resumable and visible.

Pilot: exec_rudd and sisc, 26 statements, 14 model jobs, $0.089731 estimated additional cost, zero failed jobs or uncertain requests. Full backfill runs with a $25 invocation limit and unchanged project caps.

Independent review fixed fractional topic rendering, unsaved observations in offline builds, and complete-profile observations during partial/zero-budget runs. Semantic hashes now exclude operational settings and migrate exact-compatible legacy entries. A shared persistent budget wrapper now covers named-policy and broad analysis requests. Unknown costs retain reservations; hidden transport retries are disabled for these calls. Regression tests passed.

Completed backfill: all 3,499 statements; 87 summaries and 23-category profiles; zero pending analyses. Sol reviewed 1,165 statements; Astra reviewed 20 statements and regulation disagreements for 26 profiles. Ten empty profiles remain explicit. Final verification passed 162 Python and 38 JavaScript tests. The full preservation/history/citation audit passed. A network-blocked repeat and the daily analysis path made no new paid calls. Actual-data browser checks covered officials, institutions, citations, fractional topics, histories, and a 390-pixel layout.

Budget follow-up: reserve only price tiers reachable by the conservative input bound. Confirmed HTTP 402 credit rejections release their reservations; unknown failures retain them. Both changes passed independent review. The cumulative ledger total is $19.249214, including $7.151830 still reserved for five uncertain requests. The lifetime, monthly, and daily caps are unchanged.
