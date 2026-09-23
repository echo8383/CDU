# Accompanying methods and complete numerical results

This document retains details compressed out of the four-page manuscript.
The spline setting is the main presentation of an already completed multi-probe
comparison, not a claim that spline was prospectively selected before all results.
No detector was rerun for this revision. All tables below use saved evidence;
completed normalization and reference-strength robustness results are documented
in `paper/reports/REFERENCE_ROBUSTNESS_20260923.md` and quoted in the manuscript.

## Statistical reference

The 31 fixed scorer definitions come from the project implementation
`_archive/pre_fast_cleanup_2026-09-14/root/oneliners.py`. Variance and next-point
mean deviation are motivated by the One-Liners study; the other families are
project reference extensions, not a claim that all 31 originate in that paper.
Let a window start at i, have width w, and mean mu_i. Zero-based placements:

| Family | Definition | Widths | Placement |
|---|---|---|---|
| Variance (7) | Mean squared deviation from mu_i (ddof=0) | 8,16,32,64,96,128,256 | i+floor(w/2) |
| Range (7) | Window max minus min | same as variance | i+floor(w/2) |
| Next-point deviation (7) | (mu_i-x[i+w])^2 | 1,2,3,8,16,32,64 | i+w |
| Center-placed deviation (3) | Same next-point error, placed earlier; not deviation of the center observation | 3,16,64 | i+floor(w/2) |
| Absolute difference (3) | abs(x[t]-x[t-1]), optionally smoothed with a length-w uniform convolution (`same`) | 1,4,16 | starts at index 1 |
| Median absolute deviation (2) | Median absolute distance to window median | 32,128 | i+floor(w/2) |
| Spectral entropy (2) | -sum(p log p), p from normalized demeaned-window rFFT power | 64,256 | centers; stride w/8 and linear interpolation |

Window scorers extend the nearest valid score at both edges. Spectral entropy
uses natural logarithms, assigns zero for zero spectral power, and interpolates
with endpoint extension. These centered/full-curve operations are offline.
All scored inputs use within-series average ranks; constant curves map to 0.5.
Features summarize dispersion, local prediction error/change, and spectral
irregularity; they are a declared reference, not an exhaustive statistical model.

## Data grouping and weighting

The source token is matched by `^\d+_([^_]+)_` in each series identifier.
For a held-out source, all its series are excluded from probe training. The 350
series and 23 groups are exactly those in `source_groups.json`.
Uniform sampling without replacement retains m_i=min(T_i,2048) training points.
The same sampled indices are used for every matched probe and condition. Each
retained point has weight N_s/(G_train*n_g*m_i), where N_s is the retained total.
Full-data linear training replaces m_i with T_i. Test curves remain complete.
Sample weights are not additional class balancing.

## Predictor settings and uncertainty

Logistic: liblinear, inverse L2 strength C=0.1, max_iter=300, tol=1e-4,
random_state=2024, fit_intercept=True, intercept_scaling=1, class_weight=None.
Spline: degree=3, fixed knots [0,1/3,2/3,1], include_bias=False,
extrapolation=constant; same logistic settings.
HGB: learning_rate=0.1, max_iter=32, max_leaf_nodes=7, max_depth=3,
min_samples_leaf=100, l2_regularization=1, max_bins=31,
early_stopping=False, random_state=2024. No hyperparameter search.
Probabilities are clipped to [1e-7,1-1e-7] for log-loss in bits.
Ridge score reconstruction uses alpha=1, cap2048, complete test curves and
source-macro averages of per-series R2 and Spearman; it predicts rank scores.

Single-utility percentile intervals: 10,000 paired source-bootstrap resamples,
seed2024. Paired detector contrasts: 20,000 shared draws, seed2024, plus a joint
nine-contrast centered max-standardized bootstrap interval. The nine contrasts
are all pairs of POLY/MOMENT_FT/MOMENT_ZS under linear/spline/HGB. These were
exploratory, motivated by observed similar VUS, not a preregistered family.
The separate 27-test family concerns individual CDU versus zero, not detector
differences. It includes max-bootstrap intervals and one-sided source t-tests
with Holm adjustment as exploratory sensitivity checks. Neither bootstrap nor
Holm removes dependence due to overlapping LOSO training; fits are not repeated.

Controls: exact Var-96 rank-feature copy; independent standard-normal noise;
rank(Z+2Y) with independent standard-normal Z. Noise is deterministically seeded
by control name/series identity. Synthetic labels are used only in calibration.
Duplicating a feature can change L2 penalty geometry; no noise bias subtraction.

## Complete numerical tables

### Source groups

| source      |   n_series |
|:------------|-----------:|
| CATSv2      |          1 |
| Daphnet     |          1 |
| Exathlon    |         30 |
| IOPS        |         15 |
| LTDB        |          8 |
| MGAB        |          8 |
| MITDB       |          7 |
| MSL         |          7 |
| NAB         |         23 |
| NEK         |          8 |
| OPPORTUNITY |         27 |
| Power       |          1 |
| SED         |          2 |
| SMAP        |         17 |
| SMD         |         33 |
| SVDB        |         18 |
| SWaT        |          1 |
| Stock       |          8 |
| TAO         |          2 |
| TODS        |         13 |
| UCR         |         70 |
| WSD         |         20 |
| YAHOO       |         30 |

### Full-data linear results and both VUS aggregations

| Detector           |    Raw_VUS |   Source_macro_Raw_VUS |     L_null |    L_basis |   L_detector |   L_basis_detector |   basis_utility |   detector_utility |            CDU |     CDU_CI_low |   CDU_CI_high |   positive_sources |   bootstrap_prob_source_macro_positive |   n_series |   n_sources | status                    | Raw_source                                            | Fast_source                                   |   Raw_rank |   Source_raw_rank |   Utility_rank |   CDU_rank |   Raw_to_CDU_uplift |   Source_raw_to_CDU_uplift |
|:-------------------|-----------:|-----------------------:|-----------:|-----------:|-------------:|-------------------:|----------------:|-------------------:|---------------:|---------------:|--------------:|-------------------:|---------------------------------------:|-----------:|------------:|:--------------------------|:------------------------------------------------------|:----------------------------------------------|-----------:|------------------:|---------------:|-----------:|--------------------:|---------------------------:|
| SubPCA             | 0.42241264 |             0.44040661 | 0.33695588 | 0.33744737 |   0.31934176 |         0.32622497 |  -0.00049149529 |      0.017614115   |  0.011222401   | -0.0039782055  | 0.029214035   |                 12 |                                 0.9139 |        350 |          23 | COMPLETE_CI_INCLUDES_ZERO | layer2_results/audit_raw_vus_per_series.csv           | protocol_fast_results/main/SubPCA             |          1 |                 1 |              1 |          1 |                   0 |                          0 |
| POLY               | 0.38927059 |             0.40819388 | 0.33695588 | 0.33744737 |   0.33297998 |         0.33681913 |  -0.00049149529 |      0.0039758982  |  0.00062823634 | -0.0022561888  | 0.0029397139  |                 15 |                                 0.6947 |        350 |          23 | COMPLETE_CI_INCLUDES_ZERO | layer2_results/audit_raw_vus_per_series.csv           | protocol_fast_results/main/POLY               |          2 |                 2 |              4 |          4 |                  -2 |                         -2 |
| MOMENT_FT          | 0.38640863 |             0.4063842  | 0.33695588 | 0.33744737 |   0.33651707 |         0.33751757 |  -0.00049149529 |      0.00043880681 | -7.0202553e-05 | -0.0011739957  | 0.00085076281 |                 14 |                                 0.4583 |        350 |          23 | COMPLETE_CI_INCLUDES_ZERO | layer2_results/MOMENT_FT_audited_per_series_vus.csv   | protocol_fast_results/main/MOMENT_FT          |          3 |                 3 |              5 |          6 |                  -3 |                         -3 |
| MOMENT_ZS          | 0.38322901 |             0.40294524 | 0.33695588 | 0.33744737 |   0.33681212 |         0.33752267 |  -0.00049149529 |      0.00014375518 | -7.5300616e-05 | -0.00063761656 | 0.00042382018 |                 14 |                                 0.3978 |        350 |          23 | COMPLETE_CI_INCLUDES_ZERO | layer2_results/MOMENT_ZS_audited_per_series_vus.csv   | protocol_fast_results/main/MOMENT_ZS          |          4 |                 4 |              7 |          7 |                  -3 |                         -3 |
| M2N2               | 0.28704715 |             0.34396016 | 0.33695588 | 0.33744737 |   0.3202247  |         0.3264276  |  -0.00049149529 |      0.016731176   |  0.011019774   | -0.001427615   | 0.024688599   |                 12 |                                 0.9521 |        350 |          23 | COMPLETE_CI_INCLUDES_ZERO | layer2_results/stage2_raw_vus_per_series/M2N2.csv     | protocol_fast_results/main/M2N2               |          5 |                 5 |              2 |          2 |                   3 |                          3 |
| TranAD             | 0.27540339 |             0.3148383  | 0.33695588 | 0.33744737 |   0.33229795 |         0.33469886 |  -0.00049149529 |      0.0046579229  |  0.002748508   | -0.0048205988  | 0.010657913   |                 10 |                                 0.7486 |        350 |          23 | COMPLETE_CI_INCLUDES_ZERO | layer2_results/stage2_raw_vus_per_series/TranAD.csv   | protocol_fast_results/main/TranAD             |          6 |                 6 |              3 |          3 |                   3 |                          3 |
| TimesNet           | 0.26274597 |             0.29767516 | 0.33695588 | 0.33744737 |   0.33771856 |         0.3378128  |  -0.00049149529 |     -0.00076268715 | -0.00036543151 | -0.0010981156  | 5.0795227e-05 |                 16 |                                 0.1227 |        350 |          23 | COMPLETE_CI_INCLUDES_ZERO | layer2_results/stage2_raw_vus_per_series/TimesNet.csv | protocol_fast_results/main/TimesNet           |          7 |                 7 |              9 |          8 |                  -1 |                         -1 |
| FITS               | 0.24636918 |             0.29203504 | 0.33695588 | 0.33744737 |   0.33700482 |         0.33781351 |  -0.00049149529 |     -4.8945269e-05 | -0.00036614269 | -0.0023696806  | 0.0010675259  |                 16 |                                 0.3759 |        350 |          23 | COMPLETE_CI_INCLUDES_ZERO | layer2_results/stage2_raw_vus_per_series/FITS.csv     | protocol_fast_results/main/FITS               |          8 |                 8 |              8 |          9 |                  -1 |                         -1 |
| AnomalyTransformer | 0.11176888 |             0.16949091 | 0.33695588 | 0.33744737 |   0.33662564 |         0.33697881 |  -0.00049149529 |      0.00033023998 |  0.0004685625  | -0.00055545587 | 0.0017054224  |                 11 |                                 0.7873 |        350 |          23 | COMPLETE_CI_INCLUDES_ZERO | layer2_results/audit_raw_vus_per_series.csv           | protocol_fast_results/main/AnomalyTransformer |          9 |                 9 |              6 |          5 |                   4 |                          4 |

### All matched-probe CDU estimates and intervals

| probe   | detector           |            CDU |         CI_low |       CI_high |   positive_sources |   bootstrap_prob_macro_positive | CI_covers_zero   |
|:--------|:-------------------|---------------:|---------------:|--------------:|-------------------:|--------------------------------:|:-----------------|
| linear  | SubPCA             |  0.011261032   | -0.0042392055  | 0.029645621   |                 12 |                          0.9106 | True             |
| linear  | POLY               |  0.00065159058 | -0.0021775504  | 0.0029386338  |                 16 |                          0.7014 | True             |
| linear  | MOMENT_FT          | -2.2163716e-05 | -0.0010567001  | 0.0008544892  |                 14 |                          0.4919 | True             |
| linear  | MOMENT_ZS          | -7.7531244e-05 | -0.00061293881 | 0.00039414503 |                 14 |                          0.388  | True             |
| linear  | M2N2               |  0.010953001   | -0.0016668448  | 0.024745808   |                 12 |                          0.9491 | True             |
| linear  | TranAD             |  0.0027620576  | -0.0050246021  | 0.010920436   |                 10 |                          0.7418 | True             |
| linear  | TimesNet           | -0.00034332356 | -0.0010292739  | 5.5218726e-05 |                 16 |                          0.1215 | True             |
| linear  | FITS               | -0.0004159889  | -0.0020995096  | 0.00071237291 |                 17 |                          0.3189 | True             |
| linear  | AnomalyTransformer |  0.00047161688 | -0.00049666763 | 0.0016382621  |                 11 |                          0.8063 | True             |
| spline  | SubPCA             |  0.015086931   |  0.0025627828  | 0.029642011   |                 15 |                          0.9932 | False            |
| spline  | POLY               |  0.0060399315  |  0.0024586997  | 0.0096881543  |                 16 |                          0.9997 | False            |
| spline  | MOMENT_FT          |  0.00098988287 | -7.9995123e-06 | 0.0020774904  |                 13 |                          0.9742 | True             |
| spline  | MOMENT_ZS          |  0.00010810151 | -0.00087759892 | 0.0011260167  |                  7 |                          0.5748 | True             |
| spline  | M2N2               |  0.012721629   |  0.00075384241 | 0.026143894   |                 13 |                          0.9821 | False            |
| spline  | TranAD             |  0.0048447656  | -0.0016211225  | 0.012630593   |                 10 |                          0.9168 | True             |
| spline  | TimesNet           |  0.0013265053  | -0.00015240388 | 0.0029958283  |                 12 |                          0.96   | True             |
| spline  | FITS               |  0.0010912806  | -7.5620556e-05 | 0.0022137069  |                 15 |                          0.9676 | True             |
| spline  | AnomalyTransformer |  0.00014845694 | -0.0012912352  | 0.0016660044  |                 11 |                          0.5739 | True             |
| hgb     | SubPCA             |  0.014862666   |  0.0028545781  | 0.029223489   |                 14 |                          0.9945 | False            |
| hgb     | POLY               |  0.0031388412  | -0.0016719598  | 0.007770144   |                 16 |                          0.9053 | True             |
| hgb     | MOMENT_FT          |  0.0010449354  | -0.0010383947  | 0.0035215125  |                 17 |                          0.8341 | True             |
| hgb     | MOMENT_ZS          |  0.00030391622 | -0.0012223822  | 0.001892131   |                 11 |                          0.6575 | True             |
| hgb     | M2N2               |  0.0083374715  |  0.0011964703  | 0.016027024   |                 13 |                          0.9903 | False            |
| hgb     | TranAD             |  0.0042864185  | -0.0013134531  | 0.010436825   |                 11 |                          0.9264 | True             |
| hgb     | TimesNet           |  0.0010804939  | -0.0012407845  | 0.0034881724  |                 12 |                          0.8189 | True             |
| hgb     | FITS               |  0.001421125   | -0.00011383961 | 0.0029478348  |                 13 |                          0.9666 | True             |
| hgb     | AnomalyTransformer |  0.0014264511  | -0.0021725568  | 0.0054800887  |                 12 |                          0.7632 | True             |

### All detector-only utilities and matched CDU

| probe   | detector           |   detector_utility |            CDU |
|:--------|:-------------------|-------------------:|---------------:|
| linear  | SubPCA             |      0.017646483   |  0.011261032   |
| linear  | POLY               |      0.0040148863  |  0.00065159058 |
| linear  | MOMENT_FT          |      0.00042962163 | -2.2163716e-05 |
| linear  | MOMENT_ZS          |      0.00010100314 | -7.7531244e-05 |
| linear  | M2N2               |      0.016741926   |  0.010953001   |
| linear  | TranAD             |      0.0046734212  |  0.0027620576  |
| linear  | TimesNet           |     -0.00076212372 | -0.00034332356 |
| linear  | FITS               |     -6.2032305e-05 | -0.0004159889  |
| linear  | AnomalyTransformer |      0.00034151254 |  0.00047161688 |
| spline  | SubPCA             |      0.040596395   |  0.015086931   |
| spline  | POLY               |      0.026996525   |  0.0060399315  |
| spline  | MOMENT_FT          |      0.019070576   |  0.00098988287 |
| spline  | MOMENT_ZS          |      0.018316224   |  0.00010810151 |
| spline  | M2N2               |      0.030898192   |  0.012721629   |
| spline  | TranAD             |      0.014379614   |  0.0048447656  |
| spline  | TimesNet           |      0.0059059054  |  0.0013265053  |
| spline  | FITS               |      0.0059830308  |  0.0010912806  |
| spline  | AnomalyTransformer |     -5.4527002e-05 |  0.00014845694 |
| hgb     | SubPCA             |      0.040858879   |  0.014862666   |
| hgb     | POLY               |      0.025387457   |  0.0031388412  |
| hgb     | MOMENT_FT          |      0.019266206   |  0.0010449354  |
| hgb     | MOMENT_ZS          |      0.018475647   |  0.00030391622 |
| hgb     | M2N2               |      0.032337498   |  0.0083374715  |
| hgb     | TranAD             |      0.014587374   |  0.0042864185  |
| hgb     | TimesNet           |      0.005012709   |  0.0010804939  |
| hgb     | FITS               |      0.0050709195  |  0.001421125   |
| hgb     | AnomalyTransformer |     -0.0022499466  |  0.0014264511  |

### Score reconstruction and residual decomposition

| detector           |   symmetric_rank_CDU |   symmetric_rank_CDU_CI_low |   symmetric_rank_CDU_CI_high |   symmetric_rank_positive_sources |   n_series |   predicted_VUS_series_macro |   residual_VUS_series_macro |   predicted_VUS_source_macro |   residual_VUS_source_macro |   source_macro_R2 |   source_macro_Spearman |   source_macro_MSE |   n_sources |   finite_R2_series |   finite_Spearman_series |    Raw_VUS |   Source_macro_Raw_VUS |   legacy_basis_Fast_CDU |   symmetric_CDU_rank |   raw_rank |
|:-------------------|---------------------:|----------------------------:|-----------------------------:|----------------------------------:|-----------:|-----------------------------:|----------------------------:|-----------------------------:|----------------------------:|------------------:|------------------------:|-------------------:|------------:|-------------------:|-------------------------:|-----------:|-----------------------:|------------------------:|---------------------:|-----------:|
| SubPCA             |        0.011249601   |              -0.0041538403  |                0.029395201   |                                13 |        350 |                   0.26808826 |                 0.20558524  |                   0.330406   |                  0.25355694 |      0.18943818   |             0.45699825  |       0.065459449  |          23 |                350 |                      350 | 0.42241264 |             0.44040661 |           0.011222401   |                    1 |          1 |
| POLY               |        0.00056373719 |              -0.002184448   |                0.002734843   |                                15 |        350 |                   0.36203774 |                 0.12595442  |                   0.39334983 |                  0.19004863 |      0.34637669   |             0.57861289  |       0.054227967  |          23 |                350 |                      350 | 0.38927059 |             0.40819388 |           0.00062823634 |                    4 |          2 |
| MOMENT_FT          |       -6.3305146e-05 |              -0.001241386   |                0.00089725184 |                                14 |        350 |                   0.34209001 |                 0.10457684  |                   0.37325122 |                  0.16695096 |      0.79934849   |             0.89467878  |       0.016720935  |          23 |                350 |                      350 | 0.38640863 |             0.4063842  |          -7.0202553e-05 |                    6 |          3 |
| MOMENT_ZS          |       -6.66592e-05   |              -0.00062057375 |                0.00041327941 |                                14 |        350 |                   0.33098723 |                 0.11097076  |                   0.3683514  |                  0.16826846 |      0.90441491   |             0.95065969  |       0.0079654039 |          23 |                350 |                      350 | 0.38322901 |             0.40294524 |          -7.5300616e-05 |                    7 |          4 |
| M2N2               |        0.011035243   |              -0.0019190188  |                0.025079787   |                                11 |        350 |                   0.19754431 |                 0.18108218  |                   0.25484103 |                  0.24029314 |      0.054127458  |             0.21680121  |       0.078822198  |          23 |                350 |                      350 | 0.28704715 |             0.34396016 |           0.011019774   |                    2 |          5 |
| TranAD             |        0.0026085586  |              -0.0050991716  |                0.010522926   |                                10 |        350 |                   0.12001011 |                 0.20561282  |                   0.18779885 |                  0.26009002 |     -0.0017866292 |             0.081520677 |       0.081126426  |          23 |                350 |                      350 | 0.27540339 |             0.3148383  |           0.002748508   |                    3 |          6 |
| TimesNet           |       -0.00039806527 |              -0.00095915037 |               -8.0822044e-05 |                                 1 |        350 |                   0.21769657 |                 0.099472252 |                   0.27274177 |                  0.16302633 |      0.23148663   |             0.60468367  |       0.050857523  |          23 |                350 |                      350 | 0.26274597 |             0.29767516 |          -0.00036543151 |                    8 |          7 |
| FITS               |       -0.00047311488 |              -0.0022518884  |                0.00068307437 |                                16 |        350 |                   0.26453076 |                 0.11535785  |                   0.31774229 |                  0.18491705 |      0.01270363   |             0.33903406  |       0.072986729  |          23 |                350 |                      350 | 0.24636918 |             0.29203504 |          -0.00036614269 |                    9 |          8 |
| AnomalyTransformer |        0.00043695666 |              -0.00054878228 |                0.0015753944  |                                11 |        350 |                   0.1129803  |                 0.11350985  |                   0.19324844 |                  0.16809951 |     -0.084080005  |             0.054528513 |       0.03283858   |          23 |                348 |                      348 | 0.11176888 |             0.16949091 |           0.0004685625  |                    5 |          9 |

### Controls

| probe   | detector             |            CDU |         CI_low |        CI_high |   positive_sources |   bootstrap_prob_macro_positive | CI_covers_zero   |
|:--------|:---------------------|---------------:|---------------:|---------------:|-------------------:|--------------------------------:|:-----------------|
| linear  | duplicate_Var96      | -4.3449556e-06 | -1.0479549e-05 | -1.6250864e-07 |                  7 |                          0.018  | False            |
| linear  | independent_noise    | -9.9450331e-07 | -1.1295701e-05 |  9.2276604e-06 |                  8 |                          0.4143 | True             |
| linear  | complementary_alpha2 |  0.10351366    |  0.074295222   |  0.1338603     |                 22 |                          1      | False            |
| spline  | duplicate_Var96      |  9.2070025e-05 | -0.00010368031 |  0.00030119931 |                 15 |                          0.816  | True             |
| spline  | independent_noise    | -6.729208e-06  | -4.4301967e-05 |  2.6774491e-05 |                 13 |                          0.3721 | True             |
| spline  | complementary_alpha2 |  0.09219615    |  0.068193112   |  0.1171198     |                 23 |                          1      | False            |
| hgb     | duplicate_Var96      | -2.6976278e-17 | -3.3328836e-17 | -2.0075939e-17 |                  0 |                          0      | False            |
| hgb     | independent_noise    | -2.6976278e-17 | -3.3328836e-17 | -2.0075939e-17 |                  0 |                          0      | False            |
| hgb     | complementary_alpha2 |  0.086413494   |  0.062766322   |  0.1124045     |                 22 |                          1      | False            |

### Paired differences

| probe   | detector_A   | detector_B   |     delta_CDU |         ci_low |       ci_high |   simultaneous9_low |   simultaneous9_high |   n_sources |   positive_sources |
|:--------|:-------------|:-------------|--------------:|---------------:|--------------:|--------------------:|---------------------:|------------:|-------------------:|
| linear  | POLY         | MOMENT_FT    | 0.0006737543  | -0.0020108585  | 0.002695177   |      -0.0025306726  |        0.0038781812  |          23 |                 17 |
| linear  | POLY         | MOMENT_ZS    | 0.00072912182 | -0.0017682338  | 0.0026924125  |      -0.0022946876  |        0.0037529312  |          23 |                 16 |
| linear  | MOMENT_FT    | MOMENT_ZS    | 5.5367528e-05 | -0.00062633749 | 0.00063333186 |      -0.00079734137 |        0.00090807643 |          23 |                 18 |
| spline  | POLY         | MOMENT_FT    | 0.0050500487  |  0.0017221506  | 0.0086009923  |       0.00036146531 |        0.009738632   |          23 |                 15 |
| spline  | POLY         | MOMENT_ZS    | 0.00593183    |  0.0024106771  | 0.0096076693  |       0.001056771   |        0.010806889   |          23 |                 19 |
| spline  | MOMENT_FT    | MOMENT_ZS    | 0.00088178136 |  0.00021563328 | 0.0015531837  |      -1.0057379e-05 |        0.0017736201  |          23 |                 18 |
| hgb     | POLY         | MOMENT_FT    | 0.0020939058  | -0.0019392542  | 0.0056869367  |      -0.0030499052  |        0.0072377169  |          23 |                 14 |
| hgb     | POLY         | MOMENT_ZS    | 0.002834925   | -0.0017456165  | 0.0069084289  |      -0.0030095814  |        0.0086794314  |          23 |                 16 |
| hgb     | MOMENT_FT    | MOMENT_ZS    | 0.00074101915 | -0.00042489224 | 0.0020322198  |      -0.00090031386 |        0.0023823522  |          23 |                 12 |

### Multiplicity and source influence

| probe   | detector           |            CDU |   simultaneous9_low |   simultaneous9_high |   simultaneous27_low |   simultaneous27_high |   exploratory_t_p_greater |     holm9_p |    holm27_p |   delete_source_min |   delete_source_max |   delete_source_positive_count | most_influential_source   |
|:--------|:-------------------|---------------:|--------------------:|---------------------:|---------------------:|----------------------:|--------------------------:|------------:|------------:|--------------------:|--------------------:|-------------------------------:|:--------------------------|
| linear  | SubPCA             |  0.011261032   |      -0.011538095   |        0.034060158   |       -0.014571444   |         0.037093507   |              0.10992107   | 0.87936857  | 1           |       0.0049695821  |       0.014242552   |                             23 | SWaT                      |
| linear  | POLY               |  0.00065159058 |      -0.0027518532  |        0.0040550343  |       -0.0032046702  |         0.0045078514  |              0.31465975   | 1           | 1           |       0.00031653556 |       0.001731114   |                             23 | SWaT                      |
| linear  | MOMENT_FT          | -2.2163716e-05 |      -0.0012925858  |        0.0012482584  |       -0.0014616113  |         0.0014172839  |              0.51758872   | 1           | 1           |      -0.00016239917 |       0.00030996845 |                              5 | SED                       |
| linear  | MOMENT_ZS          | -7.7531244e-05 |      -0.00074303977 |        0.00058797729 |       -0.00083158351 |         0.00067652102 |              0.61570397   | 1           | 1           |      -0.00016106725 |       6.5238959e-05 |                              3 | SED                       |
| linear  | M2N2               |  0.010953001   |      -0.0069387632  |        0.028844765   |       -0.009319204   |         0.031225206   |              0.065893849  | 0.59304464  | 1           |       0.0070971322  |       0.013234787   |                             23 | SWaT                      |
| linear  | TranAD             |  0.0027620576  |      -0.0079269722  |        0.013451088   |       -0.0093491127  |         0.014873228   |              0.25783026   | 1           | 1           |       0.00043285004 |       0.0046651665  |                             23 | SWaT                      |
| linear  | TimesNet           | -0.00034332356 |      -0.0011506853  |        0.00046403816 |       -0.0012581021  |         0.00057145499 |              0.85566304   | 1           | 1           |      -0.00036876322 |      -3.5678795e-05 |                              0 | SWaT                      |
| linear  | FITS               | -0.0004159889  |      -0.0023470933  |        0.0015151155  |       -0.0026040205  |         0.0017720427  |              0.70633759   | 1           | 1           |      -0.00052481189 |       0.00026242574 |                              1 | SWaT                      |
| linear  | AnomalyTransformer |  0.00047161688 |      -0.00094243265 |        0.0018856664  |       -0.0011305673  |         0.0020738011  |              0.20148446   | 1           | 1           |       7.9087367e-05 |       0.00065236688 |                             23 | SWaT                      |
| spline  | SubPCA             |  0.015086931   |      -0.0036276051  |        0.033801466   |       -0.005431988   |         0.035605849   |              0.022294112  | 0.17835289  | 0.56200988  |       0.010403542   |       0.017547928   |                             23 | SWaT                      |
| spline  | POLY               |  0.0060399315  |       0.0010657637  |        0.011014099   |        0.00058617378 |         0.011493689   |              0.0020252203 | 0.018226982 | 0.054680947 |       0.0051732148  |       0.0068770608  |                             23 | LTDB                      |
| spline  | MOMENT_FT          |  0.00098988287 |      -0.0004581924  |        0.0024379581  |       -0.00059781019 |         0.0025775759  |              0.042289638  | 0.25166305  | 0.90647145  |       0.00066267769 |       0.0012290525  |                             23 | SMAP                      |
| spline  | MOMENT_ZS          |  0.00010810151 |      -0.0012714279  |        0.001487631   |       -0.0014044368  |         0.0016206398  |              0.41893549   | 0.83787098  | 1           |      -0.00017701017 |       0.0004220743  |                             20 | SWaT                      |
| spline  | M2N2               |  0.012721629   |      -0.0050570364  |        0.030500294   |       -0.0067711863  |         0.032214443   |              0.035951865  | 0.25166305  | 0.82689289  |       0.0088082279  |       0.014550309   |                             23 | SWaT                      |
| spline  | TranAD             |  0.0048447656  |      -0.0050167204  |        0.014706252   |       -0.0059675267  |         0.015657058   |              0.10384466   | 0.31153398  | 1           |       0.0022476394  |       0.0056737165  |                             23 | SWaT                      |
| spline  | TimesNet           |  0.0013265053  |      -0.00085141976 |        0.0035044303  |       -0.0010614068  |         0.0037144174  |              0.060897718  | 0.25166305  | 1           |       0.00091133952 |       0.001546983   |                             23 | SWaT                      |
| spline  | FITS               |  0.0010912806  |      -0.00049314275 |        0.0026757039  |       -0.0006459067  |         0.0028284679  |              0.041203248  | 0.25166305  | 0.90647145  |       0.00085328639 |       0.0013278873  |                             23 | SMAP                      |
| spline  | AnomalyTransformer |  0.00014845694 |      -0.0018869814  |        0.0021838953  |       -0.0020832305  |         0.0023801443  |              0.42447281   | 0.83787098  | 1           |      -0.00017156574 |       0.00047351647 |                             18 | TAO                       |
| hgb     | SubPCA             |  0.014862666   |      -0.0030016403  |        0.032726973   |       -0.005209265   |         0.034934598   |              0.021615765  | 0.19454188  | 0.56200988  |       0.0097682195  |       0.017145742   |                             23 | SWaT                      |
| hgb     | POLY               |  0.0031388412  |      -0.0032150036  |        0.009492686   |       -0.0040001953  |         0.010277878   |              0.10801901   | 0.54009507  | 1           |       0.0020425949  |       0.0045275636  |                             23 | OPPORTUNITY               |
| hgb     | MOMENT_FT          |  0.0010449354  |      -0.0019542227  |        0.0040440935  |       -0.0023248509  |         0.0044147217  |              0.18936147   | 0.75744587  | 1           |       9.6011306e-05 |       0.0017077415  |                             23 | SWaT                      |
| hgb     | MOMENT_ZS          |  0.00030391622 |      -0.0017640631  |        0.0023718956  |       -0.0020196186  |         0.0026274511  |              0.35418387   | 0.75744587  | 1           |      -0.00024440085 |       0.00078708068 |                             22 | SWaT                      |
| hgb     | M2N2               |  0.0083374715  |      -0.0017729295  |        0.018447872   |       -0.0030223466  |         0.01969729    |              0.022469995  | 0.19454188  | 0.56200988  |       0.0063516073  |       0.0095534409  |                             23 | TAO                       |
| hgb     | TranAD             |  0.0042864185  |      -0.0036698282  |        0.012242665   |       -0.0046530405  |         0.013225878   |              0.089346726  | 0.53608036  | 1           |       0.0022695021  |       0.0052088639  |                             23 | SWaT                      |
| hgb     | TimesNet           |  0.0010804939  |      -0.0021159345  |        0.0042769222  |       -0.0025109408  |         0.0046719286  |              0.19642041   | 0.75744587  | 1           |       0.00038061724 |       0.0018232532  |                             23 | TAO                       |
| hgb     | FITS               |  0.001421125   |      -0.00066810157 |        0.0035103515  |       -0.00092628276 |         0.0037685327  |              0.046684794  | 0.32679356  | 0.93369589  |       0.0010532045  |       0.0018786051  |                             23 | TAO                       |
| hgb     | AnomalyTransformer |  0.0014264511  |      -0.0037488209  |        0.0066017231  |       -0.0043883676  |         0.0072412698  |              0.24237059   | 0.75744587  | 1           |      -7.2515677e-06 |       0.0022390182  |                             22 | SWaT                      |

### Five-seed summary

| detector           |          mean |            sd |       minimum |       maximum |   positive_seeds |   ci_positive_seeds |
|:-------------------|--------------:|--------------:|--------------:|--------------:|-----------------:|--------------------:|
| SubPCA             | 0.015047495   | 7.5451987e-05 | 0.014931808   | 0.015104903   |                5 |                   5 |
| POLY               | 0.0061962014  | 0.00013361142 | 0.0060399315  | 0.0063433662  |                5 |                   5 |
| MOMENT_FT          | 0.00089395166 | 7.7807331e-05 | 0.00081826114 | 0.00098988287 |                5 |                   0 |
| MOMENT_ZS          | 0.00013632465 | 5.9418675e-05 | 7.4141746e-05 | 0.00021023811 |                5 |                   0 |
| M2N2               | 0.012721648   | 5.3330272e-05 | 0.012645737   | 0.012783829   |                5 |                   5 |
| TranAD             | 0.0047491759  | 8.8462011e-05 | 0.0046753075  | 0.004846955   |                5 |                   0 |
| TimesNet           | 0.0012500765  | 6.7391376e-05 | 0.0011476345  | 0.0013265053  |                5 |                   1 |
| FITS               | 0.00109622    | 5.9239246e-05 | 0.001010356   | 0.0011636138  |                5 |                   0 |
| AnomalyTransformer | 0.00016352664 | 4.1511487e-05 | 0.00011840209 | 0.00021811136 |                5 |                   0 |

### Reference removals

| variant                                |   rho_vs_full |   max_abs_change |
|:---------------------------------------|--------------:|-----------------:|
| basis_spline_seed0_absolute_difference |    1          |    0.00030517132 |
| basis_spline_seed0_centered_placement  |    0.98333333 |    0.0001516286  |
| basis_spline_seed0_mad                 |    1          |    0.00055623896 |
| basis_spline_seed0_next_difference     |    0.96666667 |    0.0026922007  |
| basis_spline_seed0_range               |    1          |    0.00054481135 |
| basis_spline_seed0_spectral_entropy    |    1          |    0.0001495931  |
| basis_spline_seed0_variance            |    0.91666667 |    0.0013241021  |

## Interpretation and revision provenance

Negative estimates and the full-data linear noise interval excluding zero are
retained. Positive paired POLY/MOMENT spline contrasts do not imply the same
significance under other probes; see the complete contrast table. Rank agreement
does not establish invariance of individual effects or simultaneous significance.
The main manuscript retains the absolute-utility multiplicity finding in concise
form. No original evidence files are removed or overwritten by this asset script.

Bibliographic verification used the official ACL page for conditional probing
(https://aclanthology.org/2021.emnlp-main.122/) and the publisher abstract for the
related drift study (https://www.sciencedirect.com/science/article/pii/S1568494626018089).
The latter supports the forecast-error/window-statistics description; this is
not a claim to have reviewed all of that paper's supplementary experiments.
