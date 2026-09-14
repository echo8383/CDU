# Experiment map

## Primary computation

1. Compute a shared fixed-`C=0.1` source-LOSO baseline (`L_null`, `L_basis`).
2. Evaluate the nine frozen detector caches (`L_detector`, `L_basis_detector`).
3. Derive detector-only utility and CDU per series and per source.
4. Aggregate sources equally and calculate paired source-bootstrap intervals.
5. Join the result with benchmark and source-macro Raw VUS offline.

The primary detector pool is SubPCA, POLY, MOMENT_FT, MOMENT_ZS, M2N2,
TranAD, TimesNet, FITS, and AnomalyTransformer.

## Existing supporting evidence

- Exact-duplicate control: redundant basis copies produce CDU near zero.
- Independent-noise control: establishes an empirical finite-sample floor.
- Complementary alpha controls: known injected label information produces a
  positive dose-response pattern.
- Stage-2 audits: establish score-cache coverage, provenance and alignment.

These exhaustive controls are retained as supporting evidence and no longer
block the deadline-focused main run.

## Explicitly out of scope

- detector retraining or new detectors;
- nested inner-CV hyperparameter search;
- hard-subset detector claims;
- ensemble selection and CDU-guided training;
- historical leaderboard parity;
- additional probe or basis-sensitivity sweeps before the primary table.

## Final paper outputs

The final table reports benchmark Raw VUS, source-macro Raw VUS,
detector-only utility, CDU, paired source-level 95% confidence interval,
positive-source fraction, and the corresponding ranks. The main figure is a
Raw-VUS-versus-CDU scatter paired with the CDU evaluation schematic.

