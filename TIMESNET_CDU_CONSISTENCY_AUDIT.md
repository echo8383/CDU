# TimesNet CDU Consistency Audit

## Scope

This is an offline audit of the existing `TimesNet_cdu_per_series.csv`. It did not rerun TimesNet, refit CDU probes, modify the estimator, or start another detector.

## Finding on the legacy `P(CDU>0)=0.4914` field

The legacy value `0.49142857142857144` is exactly `172 / 350`, i.e. the **5-fold positive-series ratio** (`CDU_i > 0`). It is not a bootstrap probability for the macro CDU. The old field name `P_CDU_gt_0` was therefore ambiguous/misleading and must not be interpreted as `P(macro CDU > 0)`.

## Recomputed statistics from existing OOF per-series rows

|   folds |   n_series |   unique_series |   macro_mean_CDU_bits |    median_CDU_bits |   positive_series_count |   positive_series_ratio |   L0_bits_macro |   L1_bits_macro |   bootstrap_CI_low |   bootstrap_CI_high |   bootstrap_prob_macro_positive |   bootstrap_seed |   bootstrap_replicates |
|--------:|-----------:|----------------:|----------------------:|-------------------:|------------------------:|------------------------:|----------------:|----------------:|-------------------:|--------------------:|--------------------------------:|-----------------:|-----------------------:|
|       5 |        350 |             350 |    -0.000268865784651 | -6.51643906615e-06 |                     172 |          0.491428571429 |  0.891308442946 |  0.891577308731 | -0.000431832879654 |  -0.000112892288156 |                          0.0006 |             2024 |                  10000 |
|      10 |        350 |             350 |    -0.000201763773896 | -0.000182745885539 |                     145 |          0.414285714286 |  0.895784620868 |  0.895986384642 | -0.000301452741095 |  -0.000105411453047 |                          0.0001 |             2024 |                  10000 |

The requested series-level paired bootstrap is the 5-fold row because that is the primary protocol. It uses 10,000 resamples of the 350 paired per-series CDU deltas with seed 2024.

## Per-fold held-out losses (macro mean across held-out series)

### 5-fold

|   fold |   n_series |   L0_bits_macro |   L1_bits_macro |     CDU_bits_macro |   positive_series_ratio |
|-------:|-----------:|----------------:|----------------:|-------------------:|------------------------:|
|      0 |         70 |  0.864912195205 |  0.865595119095 | -0.000682923889117 |          0.371428571429 |
|      1 |         70 |  0.914756841282 |  0.915744682059 | -0.000987840776677 |          0.4            |
|      2 |         70 |  0.895663816154 |  0.89594169445  | -0.000277878295579 |          0.242857142857 |
|      3 |         70 |  0.873937328778 |  0.873383232445 |  0.000554096333069 |          0.8            |
|      4 |         70 |  0.90727203331  |  0.907221815605 |  5.02177050493e-05 |          0.642857142857 |

### 10-fold

|   fold |   n_series |   L0_bits_macro |   L1_bits_macro |     CDU_bits_macro |   positive_series_ratio |
|-------:|-----------:|----------------:|----------------:|-------------------:|------------------------:|
|      0 |         35 |  0.904400353363 |  0.904666921155 | -0.000266567791997 |          0.314285714286 |
|      1 |         35 |  0.869065484953 |  0.869530264239 | -0.000464779286322 |          0.428571428571 |
|      2 |         35 |  0.888354751184 |  0.888569199136 | -0.000214447951963 |          0.428571428571 |
|      3 |         35 |  0.904176938078 |  0.904899828548 | -0.000722890469884 |          0.285714285714 |
|      4 |         35 |  0.896094974143 |  0.896359068647 | -0.000264094504845 |          0.257142857143 |
|      5 |         35 |  0.901137875669 |  0.901375711739 | -0.000237836069758 |          0.314285714286 |
|      6 |         35 |  0.896646513038 |  0.897047705581 | -0.000401192542343 |          0.2            |
|      7 |         35 |  0.877325375911 |  0.876918240593 |  0.000407135318187 |          0.714285714286 |
|      8 |         35 |  0.874752645444 |  0.874789820044 | -3.71746001764e-05 |          0.428571428571 |
|      9 |         35 |  0.9458912969   |  0.94570708674  |  0.000184210160145 |          0.771428571429 |

For every saved row, `CDU_bits = L0_bits - L1_bits` holds to numerical precision. Both 5-fold and 10-fold files contain 350 unique, finite series rows.

## Probe parity / input audit

- Probe configuration found in `fast_cdu_cached.py`: `LogisticRegression(C=.1,solver='liblinear',class_weight='balanced',max_iter=300,random_state=0)`.
- M0 uses the 31-dimensional basis matrix only: PASS.
- M1 uses the same basis matrix plus exactly one extra rank-normalized TimesNet score column: PASS.
- The source constructs `X0`, `X1`, and `Y` from the same outer-fold training series; M0 and M1 use identical solver, C, class weighting, iteration cap, and random state.

## Conclusion

Classification: **A + B; not C.** There is a reporting-field error: `0.4914` is `positive_series_ratio`, not `bootstrap_prob_macro_positive`. Separately, TimesNet has a stable negative finite-sample predictive increment under this frozen protocol: both 5-fold and 10-fold macro estimates are negative and the 5-fold paired-bootstrap interval is entirely below zero. This is an estimation outcome, not a claim of negative mutual information. The saved M0/M1 identity and code-level probe parity show no evidence here of an estimator implementation failure.

## Correct field names going forward

- `positive_series_ratio`: fraction of 350 held-out per-series CDU values > 0 (5-fold: 0.4914285714).
- `bootstrap_prob_macro_positive`: fraction of bootstrap macro CDU means > 0 (5-fold: 0.0006, i.e. 6/10000 resamples).
