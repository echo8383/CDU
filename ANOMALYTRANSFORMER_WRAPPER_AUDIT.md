# AnomalyTransformer wrapper audit

The audit checks wrapper config, filename-derived training prefix, full test score length, finite cached score, cached-score reproducibility, raw-data window VUS, and score-negation diagnostic. See `layer2_results/anomalytransformer_orientation_audit.csv` and integrity/alignment CSVs. No score orientation is changed by this diagnostic.

## Constant-score follow-up

The two flagged files are:

- `531_SMAP_id_1_Sensor_tr_1811_1st_4510.csv` (7,244 points; 81 labeled anomalies)
- `536_SMAP_id_6_Sensor_tr_2160_1st_5600.csv` (8,640 points; 101 labeled anomalies)

Both cached curves are exactly all zeros (`unique_count=1`, variance `0.0`). Their raw inputs are not both constant: the first has two unique values and standard deviation `0.02350`; the second has 8,640 unique values and standard deviation `0.78030`. Thus this is detector-output collapse, not an input-file or alignment collapse. The manifest hashes match the cache and fixed-seed reruns reproduce each curve exactly (`max_abs_diff=0`).

The pinned wrapper calls TSB-AD's `run_Semisupervise_AD('AnomalyTransformer', train_prefix, full_evaluation_sequence, win_size=50, lr=0.001)`, with seed 2024. The implementation's decision function forms the continuous energy score from reconstruction loss weighted by the attention discrepancy and takes the final point of each reconstruction window; no binary thresholding, score negation, padding shift, or post-hoc normalization is applied by the wrapper. `VUS(score)` is higher than `VUS(-score)` on average (0.1117688782 vs 0.1047343933), ruling out a global sign reversal.

**Disposition:** length, finite, label/basis alignment, hash reproducibility, and score orientation checks PASS. Overall audit remains **FAIL** under the project's strict rule because two series have collapsed constant outputs. No evidence indicates a CDU implementation problem; the failure is detector-output collapse on two SMAP series.

## Targeted rerun confirmation (seed 2024)

Both flagged series were rerun once under the identical pinned wrapper and hyperparameters. The reruns reproduced the cached all-zero curves exactly (`max_abs_cached_rerun=0.0`, `unique_count=1`, `std=0.0`). For `531_SMAP...`, the 1,811-point training prefix is exactly constant (`min=max=1.0`, `std=0`), which is a sufficient data-level explanation for collapse. For `536_SMAP...`, the 2,160-point training prefix is nonconstant (`min=0.502197`, `max=0.692341`, `std=0.054915`), yet the same implementation still yields an all-zero score; this is a reproducible model/optimization collapse specific to that input, not stochastic noise. Diagnostic details are in `layer2_results/anomalytransformer_collapse_diagnostic.csv`.
