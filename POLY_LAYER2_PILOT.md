# POLY Layer-2 CDU pilot

Scope: three sequences that passed strict Gate R0 for POLY. No Sub-PCA or other detector was run. This is an engineering pilot, not a benchmark conclusion.

Point-wise alignment is exact for all 919,219 rows (see `layer2_results/poly_alignment_check.csv`): score and basis files contain the same three filenames, timestamps, and labels. Basis columns are per-series rank-normalized one-liner curves, matching the CDU probe protocol.

## Sanity checks

```json
{
  "self_copy_abs_cdu": 0.003275381601953805,
  "monotonic_copy_abs_cdu": 0.003275381601953805,
  "random_abs_cdu": 0.0002968535334031778,
  "added_signal_monotonic": true,
  "sanity_pass": true
}
```

## Controls

| control          |   L0_bits |   L1_bits |     CDU_bits |         NCDU |   series_count |
|:-----------------|----------:|----------:|-------------:|-------------:|---------------:|
| Var96_self       |   1.49728 |  1.50056  | -0.00327538  | -0.00482286  |              3 |
| Var96_monotonic  |   1.49728 |  1.50056  | -0.00327538  | -0.00482286  |              3 |
| Random           |   1.49728 |  1.49699  |  0.000296854 |  0.000450681 |              3 |
| AddedSignal_0    |   1.49728 |  1.50056  | -0.00327538  | -0.00482286  |              3 |
| AddedSignal_0.1  |   1.49728 |  0.999161 |  0.498121    |  0.252743    |              3 |
| AddedSignal_0.25 |   1.49728 |  0.876361 |  0.620921    |  0.338817    |              3 |
| AddedSignal_0.5  |   1.49728 |  0.802015 |  0.695267    |  0.385925    |              3 |
| AddedSignal_1    |   1.49728 |  0.798792 |  0.69849     |  0.388255    |              3 |

## POLY result

| detector   |   pilot_series_count |   raw_vus_mean |   basis_fixed_vus_mean |   L0_bits |   L1_bits |   CDU_bits |       NCDU |   CDU_series_sd | estimator                                                |
|:-----------|---------------------:|---------------:|-----------------------:|----------:|----------:|-----------:|-----------:|----------------:|:---------------------------------------------------------|
| POLY       |                    3 |        0.34851 |               0.497171 |   1.49728 |   1.51855 | -0.0212676 | -0.0068644 |       0.0393383 | 3-fold whole-series OOF logistic, rank-normalized scores |
The negative POLY pilot CDU is not a benchmark claim: it is based on only three heterogeneous sequences and has a series-level SD of 0.0393 bits. The controls pass, but this pilot must not be used for detector ranking or general conclusions.
