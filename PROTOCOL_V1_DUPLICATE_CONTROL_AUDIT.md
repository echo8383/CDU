# Protocol v1 exact-duplicate control audit

Audit date: 2026-09-11  
Control: `exact_duplicate_Var-96`  
Construction: detector/control feature is an exact copy of the predeclared
`Var-96` basis column (basis index 4).  
Protocol: `CDU-protocol-v1`, 23-source LOSO with inner five-fold source-grouped
selection and source-macro held-out log-loss.

## Result

| Quantity | Value |
|---|---:|
| Source-macro CDU | -0.000003391268 bits |
| Paired source-cluster bootstrap 95% CI | [-0.000009019325, 0.000000559652] |
| Positive-source fraction | 0.347826 (8/23) |
| Bootstrap probability source-macro CDU > 0 | 0.0616 |
| Series | 350/350 unique |
| Sources | 23/23 |

## Integrity checks

- All `L_null`, `L_basis`, `L_detector`, `L_basis_detector`, and CDU values are finite: **PASS**.
- Every benchmark series occurs exactly once: **PASS**.
- `L_null` is bitwise identical to the frozen shared baseline for every series: **PASS**, maximum absolute difference `0.0`.
- `L_basis` is bitwise identical to the frozen shared baseline for every series: **PASS**, maximum absolute difference `0.0`.
- Row order/series identity matches the shared baseline after canonical sorting: **PASS**.
- `CDU = L_basis - L_basis_detector`: **PASS**, maximum floating-point residual `9.71e-17`.
- Selected basis and basis+duplicate hyperparameters are both `C=0.01` in all outer sources.

## Decision

**DUPLICATE CONTROL PASS.** The point estimate is practically zero and slightly
negative; its 95% source-cluster interval contains zero and is not strictly
positive. The frozen evaluator therefore does not assign detectable positive
conditional utility to an exact copy of an already available basis feature.

This passes the duplicate-specific portion of the formal control gate. It does
not by itself authorize the detector pilot: independent noise, all complementary
alphas, the clean/resume regression, and final combined acceptance remain
required.

Generated numeric sources (ignored by Git):

```text
protocol_v1_results/controls/exact_duplicate_Var-96/PER_SERIES.csv
protocol_v1_results/controls/exact_duplicate_Var-96/PER_SOURCE.csv
protocol_v1_results/controls/exact_duplicate_Var-96/SUMMARY.csv
protocol_v1_results/controls/shared_baseline/BASELINE_PER_SERIES.csv
```
