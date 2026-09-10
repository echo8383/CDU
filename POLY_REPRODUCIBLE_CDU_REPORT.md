# POLY Reproducible CDU Report

R0 pinned environment: `official_historical`, commit `8b363e350ae047a8115a594d1e9da64aae09b852`, seed 2024. Historical leaderboard VUS is not mixed into this result; raw VUS below is the pinned local VUS.

## POLY result (macro, series-weighted)

- Pinned raw VUS: `0.389270589096`
- CDU (5-fold): `0.00858770793368` bits
- Paired series bootstrap 95% CI: `[0.00733735524138, 0.00984282074941]` bits
- P(CDU > 0): `0.828571`
- CDU (10-fold): `0.00873021655952` bits
- 5/10-fold difference: `-0.000142508625845` bits

Controls are in `layer2_results/poly_full_controls.csv`; per-series held-out losses and deltas are in `layer2_results/poly_full_cdu_per_series.csv`. Negative finite-sample CDU values are retained and are not clipped.
