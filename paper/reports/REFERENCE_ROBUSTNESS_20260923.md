# Reference and score-interface robustness (completed 2026-09-23)

## Question and fixed population

These offline experiments ask whether the primary spline CDU ordering survives changes to (i) the label-free detector-score interface and (ii) the declared statistical reference. They use the same frozen point-wise outputs from all nine detectors, all 350 TSB-AD-U series, 23 source-held-out test groups, sampled training capped at 2,048 points per series, and full test curves. No detector was rerun. The primary condition is the within-series average-rank interface for the detector and all 31 reference scores.

The normalization experiment keeps the **ranked 31-feature reference fixed** and changes only the detector score to within-series min-max or Gaussianized z-score (`Phi(z)`). The reference-growth experiment keeps the ranked detector score fixed and cumulatively adds reference families: 7 variance features; 14 variance/range; 24 including next-point and centered deviations; 29 including absolute differences and MAD; then the primary full 31 including spectral entropy. Thus the two experiments test different changes and their estimates should not be pooled.

## Result summary

| Changed input | Setting | Reference features | Rank rho vs primary | Same top-two set | Same top-four set | Largest absolute CDU change (bits) |
|:--|:--|--:|--:|:--:|:--:|--:|
| Detector score | Min-max | 31 | 0.517 | Yes | No | 0.008991 |
| Detector score | Gaussianized z-score | 31 | 0.933 | Yes | Yes | 0.007472 |
| Reference | Variance | 7 | 0.933 | Yes | Yes | 0.003726 |
| Reference | Variance + range | 14 | 0.950 | Yes | Yes | 0.003215 |
| Reference | + local deviation | 24 | 1.000 | Yes | Yes | 0.000368 |
| Reference | + dispersion/change | 29 | 1.000 | Yes | Yes | 0.000150 |

The *set* of the first two detectors is unchanged in all six tests. Their order reverses under the two smallest references and under min-max scaling. The top-four set is unchanged in the four reference-growth conditions and in Gaussianized z-score, but changes under min-max scaling. Spearman correlations summarize all nine ranks, not individual-detector confidence.

Source-macro held-out basis log-loss falls from 0.298737 bits (7 features) to 0.297966 (14), 0.293178 (24), 0.294518 (29), and 0.289121 (full 31). It does not decrease at every step; finite-probe performance is not guaranteed to be monotone as features are added.

### All nine CDU estimates (source-macro bits)

| Detector | Primary rank-31 | Min-max-31 | Gaussian-31 | Variance-7 | Var/range-14 | Local-24 | Dispersion-29 |
|:--|--:|--:|--:|--:|--:|--:|--:|
| SubPCA | 0.015087 | 0.011179 | 0.022559 | 0.013539 | 0.013319 | 0.014848 | 0.015157 |
| POLY | 0.006040 | -0.002952 | 0.008335 | 0.006250 | 0.005826 | 0.006146 | 0.006148 |
| MOMENT-FT | 0.000990 | -0.000826 | 0.001064 | 0.000706 | 0.000658 | 0.000916 | 0.000932 |
| MOMENT-ZS | 0.000108 | -0.002142 | -0.001134 | -0.000063 | 0.000051 | 0.000072 | 0.000087 |
| M2N2 | 0.012722 | 0.018088 | 0.015072 | 0.016448 | 0.015936 | 0.012353 | 0.012572 |
| TranAD | 0.004845 | 0.002326 | 0.002584 | 0.006422 | 0.006260 | 0.004875 | 0.004844 |
| TimesNet | 0.001327 | -0.000395 | 0.000243 | 0.001250 | 0.001382 | 0.001379 | 0.001403 |
| FITS | 0.001091 | -0.000271 | 0.000748 | 0.001410 | 0.001194 | 0.001308 | 0.001235 |
| AnomalyTransformer | 0.000148 | -0.000084 | -0.000673 | -0.000087 | -0.000083 | 0.000125 | 0.000131 |

The reference-growth results support the primary claim that the leading *group* is not selected by one arbitrary reference size. They do not prove every coefficient or individual contrast is invariant. In particular, min-max scaling moves POLY from primary CDU rank 3 (0.006040 bits) to rank 9 (-0.002952 bits). The main paper therefore states explicitly that the broader ordering is sensitive to the detector-score interface. This does not change the frozen primary rank protocol; it defines its scope. We do not infer that outliers caused the min-max difference without a separate diagnostic.

## Validation and source files

- Every one of the six variants has nine detector summaries. Each summary has 350 unique series from 23 sources; the four reference-growth variants also have complete 23-source basis baselines.
- Independently re-averaging per-series CDU within sources and then equally across sources reproduces all 54 detector summaries, with maximum absolute discrepancy `5.204e-18` bits.
- Queue progress reports all six variants COMPLETE. Error logs are empty.
- Full per-detector estimates and bootstrap intervals: `paper/evidence/reference_robustness/DETECTORS.csv`.
- Rank comparisons: `paper/evidence/reference_robustness/STABILITY.csv`.
- Per-series losses and run manifests: `protocol_reference_robustness/{normalization,strength}/cap2048/`.
- Primary spline values: `paper/evidence/rank_probe_extension/DETECTORS.csv` and `protocol_rank_probe_results/cap2048/spline/`.

The manuscript reports only the compact rank and interface conclusions; this report preserves the complete detector matrix and the material min-max exception.
