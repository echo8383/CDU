# CDU Protocol Fast v1

Status: frozen for the deadline-focused ICASSP main run on 2026-09-14.

This protocol keeps the scientific core of Protocol v1 and removes the costly
inner hyperparameter search. Existing `protocol_v1_results/` files are retained
as historical diagnostics and are never mixed with fast-protocol results.

## Fixed population and inputs

- 350 TSB-AD-U univariate series grouped into the existing 23 source datasets.
- The existing 31-dimensional declared low-complexity statistical basis.
- The nine audited, cached detector point-wise score curves; detectors are not rerun.
- Per-series average-rank detector normalization; ties use average ranks and constants map to 0.5.
- Seed 2024.

## Evaluation

- Outer evaluation: leave one complete source dataset out (23-source LOSO).
- Probe: L2 logistic regression, `solver=liblinear`, `class_weight=None`,
  `max_iter=300`, `random_state=2024`.
- Regularization is fixed globally at `C=0.1` for every condition and detector.
  There is no inner cross-validation and no detector-specific tuning.
- Training weights and evaluation aggregation remain source -> series -> timestamp
  hierarchical equal weighting.
- Loss is binary log-loss in bits.

For each held-out series the protocol records:

```text
L_null, L_basis, L_detector, L_basis_detector,
basis_utility=L_null-L_basis,
detector_utility=L_null-L_detector,
CDU=L_basis-L_basis_detector
```

`L_null` and `L_basis` are computed once using the same fixed `C=0.1` basis
probe and cached for all detectors. Each detector therefore requires only two
fits per held-out source, or 46 fits in total.

## Uncertainty and reporting

- Primary aggregate: equal-weight source macro mean.
- CDU uncertainty: 10,000-replicate paired source-cluster bootstrap, seed 2024.
- Negative finite-sample CDU values are not clipped.
- Report benchmark Raw VUS separately; do not mix historical leaderboard values.

Duplicate, independent-noise, and a complementary synthetic score may be run as
small diagnostic controls. They are reported transparently but are not blocking
engineering gates for the deadline-focused main run.

