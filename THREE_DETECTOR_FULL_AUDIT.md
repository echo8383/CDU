# Three Detector Full Audit

| Detector           |   Raw_VUS |   CDU_5fold_bits |   CDU_10fold_bits |   CDU_median_5fold |   CDU_CI_low |   CDU_CI_high |   positive_series_ratio |   bootstrap_prob_macro_positive | Score_integrity   | Alignment   | Reproducibility   | Audit_status   |
|:-------------------|----------:|-----------------:|------------------:|-------------------:|-------------:|--------------:|------------------------:|--------------------------------:|:------------------|:------------|:------------------|:---------------|
| POLY               |  0.389271 |      0.00850339  |       0.00847239  |        0.00735762  |  0.00734496  |   0.00962584  |                0.811429 |                          1      | PASS              | PASS        | PASS              | PASS           |
| SubPCA             |  0.422413 |      0.0599956   |       0.0616257   |        0.0536206   |  0.0545741   |   0.0653887   |                0.914286 |                          1      | PASS              | PASS        | PASS              | PASS           |
| AnomalyTransformer |  0.111769 |     -0.000199523 |      -0.000114196 |       -1.34421e-05 | -0.000618048 |   0.000202526 |                0.485714 |                          0.1648 | PASS              | PASS        | PASS              | FAIL           |

## Controls

| control      |   folds |   macro_CDU_bits |   positive_series_ratio |
|:-------------|--------:|-----------------:|------------------------:|
| Var96_self   |       5 |     -2.91335e-07 |                0.4      |
| Var96_affine |       5 |      1.65542e-06 |                0.482857 |
| Random       |       5 |      2.2475e-07  |                0.522857 |

## Field definitions

- `positive_series_ratio`: fraction of the 350 held-out per-series CDU values greater than zero.
- `bootstrap_prob_macro_positive`: proportion of 10,000 series-level bootstrap macro means greater than zero.

## Audit disposition

- POLY and SubPCA satisfy the current cache-integrity, alignment, reproducibility, and CDU recomputation checks.
- AnomalyTransformer passes length/finite/alignment/hash/reproducibility checks, and `VUS(-score)` is lower than `VUS(score)` on average, so there is no evidence of a global score-direction inversion. However, two cached series have constant zero-variance scores (`531_SMAP_id_1_Sensor_tr_1811_1st_4510.csv` and `536_SMAP_id_6_Sensor_tr_2160_1st_5600.csv`). Under the stated audit rule, this makes its overall `Audit_status=FAIL`; this is a detector-output collapse flag, not an alignment failure.
- The formal Raw VUS values in this table are recomputed from the current caches using the raw-data evaluation window. The older SubPCA value `0.4352736244` was a preliminary offline value and is superseded here by `0.4224126371`.
