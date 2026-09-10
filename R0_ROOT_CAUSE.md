# Gate R0 — official VUS reproduction audit

**Gate R0: FAIL. Real CDU is blocked.**

## ROOT_CAUSE

The official VUS table and the checked-out TSB-AD runner use different `find_length_rank` semantics. The official table uses the older behavior that falls back to window 125 when the ACF peak is below lag 3. Commit `cd66bc1` (Fix logic bug discarding periods smaller than 5) removed that `<3` fallback. The current checkout is `8b363e350ae047a8115a594d1e9da64aae09b852`.

For `039_WSD_id_11_WebService_tr_1746_1st_1846.csv`, the current runner selects window 4, while the official score is reproduced with window 125. This is evaluator-version drift, not data provenance drift; the two data files are byte-identical.

## Results

- `uni_vuspr.csv` and official `uni_mergedTable_VUS-PR.csv`: byte-identical, 350 × 40, max/mean abs diff 0/0, SHA-256 `7491e31f44f84ad38b17dbff4b5243b50782868c82e7b491f5c174eefbe5889d`.
- Default window 100: mean abs diff 0.0377016, max 0.0763970.
- `find_length_rank` window: mean abs diff 0.0006671, max 0.00381175.
- Official HP: `POLY={'periodicity':1,'power':4}`, `Sub_PCA={'periodicity':1,'n_components':None}`, `KShapeAD={'periodicity':1}`.
- POLY HP reproduction: all three sampled diffs < 5e-16.
- Sub-PCA HP reproduction residuals: 8.50e-5, 4.32e-5, 8.96e-9.
- Current runner on 039 selects window 4 and gives Sub-PCA diff 0.2902, POLY diff 0.0267.

## Gate decision

**FAIL / STOP.** Freeze the evaluator version used to generate the official table (or obtain its historical score cache), rerun reproduction, and require `abs diff <= 1e-6` before real CDU.

Deliverables: `provenance_audit.csv`, `r0_ablation.csv`, `layer2_results/r0_hp_ablation.csv`, and `layer2_results/r0_runner_parity.csv`.

## Compatibility implementation update

`r0_official_compat.py` and `r0_runner_official_compat.py` now implement and
exercise the historical lower-bound guard without modifying Layer-2 code.
The six existing R0 samples select windows 142, 125, and 125 as expected.
POLY reproduces all three official values below `5e-16`; Sub-PCA residuals are
`8.50e-5`, `4.32e-5`, and `8.96e-9`. Thus the window-version root cause is
fixed, while the remaining Sub-PCA residual is a separate score-generation or
dependency-version discrepancy and must not be silently accepted as R0 PASS.
