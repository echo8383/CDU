# POLY historical full R0 — final status

## Decision: B. R0 FAIL — stop before CDU

The explicit `official_historical` mode successfully fixes sequence 141:

- official: `0.927581382366544`
- reproduced: `0.9275813823665443`
- absolute difference: `3.33e-16`

However, full 350-series validation cannot pass with the available historical
artifacts. The first new strict failure is:

| series | official VUS | reproduced VUS | abs diff | length | window |
|---|---:|---:|---:|---:|---:|
| `170_MITDB_id_1_Medical_tr_17675_1st_17775.csv` | 0.080444551226 | 0.053049309339 | 0.027395241887 | 500000 | 125 |

The mode is deterministic (seed 2024), uses raw full feature data, official
`power=4`, and historical-compatible `find_length_rank`. A historically older
power-2 variant also fails (difference `0.027895988460`). Additional failures
observed before worker cancellation were 184 (difference `5.98e-05`) and 188
(difference `7.76e-06`), but they were not pursued after the first failure.

The output is not 350/350, so no full-R0 PASS claim is made and no Layer-2 CDU
was executed. The `1e-6` threshold was not relaxed, no sequence was excluded,
and no official value was modified.

Artifacts:

- `POLY_HISTORICAL_COMPAT.md`
- `layer2_results/poly_historical_full_r0.csv` (sequential partial audit)
- `layer2_results/poly_historical_workers/*.json` (parallel partial audit)
- `layer2_results/poly_170_provenance_ablation.csv`
- `R0_POLY_170_FINAL.md`
