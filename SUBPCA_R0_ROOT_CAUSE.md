# Sub-PCA R0 residual audit

## Status

R0 remains **FAIL** under the required `1e-6` tolerance. No CDU was run.

## Audit scope

Three existing R0 sequences were audited:

`010_NAB_id_10_WebService_tr_500_1st_271.csv`,
`039_WSD_id_11_WebService_tr_1746_1st_1846.csv`, and
`331_UCR_id_29_Facility_tr_50000_1st_837400.csv`.

## Findings

1. **Window selection is fixed.** Compatibility windows are 142, 125, and
   125. The former 039 window-4 failure is gone.
2. **The residual is not VUS implementation drift.** The official-repository
   `TSB_AD.evaluation.basic_metrics.generate_curve` and the local
   `vus_eval.basic_metrics.generate_curve` return identical VUS values for the
   same score, label, and compatibility window.
3. **The residual is not score post-processing or ordering.** The existing raw
   and z-score score arrays have Spearman correlation 1.0 and identical rank
   arrays on all three sequences. Recomputing VUS from either gives the same
   residual. VUS depends on score ordering, so the observed difference is not
   caused by a monotone score scale.
4. **Sub-PCA output itself is the remaining source.** With compatibility
   windows and official HP `{'periodicity': 1, 'n_components': None}`, the
   reproduced Sub-PCA VUS residuals are:

   ```text
   010: 8.499484e-05
   039: 4.321483e-05
   331: 8.962635e-09
   ```

   The official point-wise Sub-PCA `.npy` files are not present in the local
   repository or its tracked history, so a direct score-array diff against the
   official output is unavailable. The residual therefore localizes to the
   detector-output provenance rather than the VUS integration or window.

## Most likely detector-output provenance issue

The current repository's `PCA.py` includes the normalization changes from
commit `a79f315` (`normalize=True`, per-window `zscore` before standardization),
while the official leaderboard table has no surviving point-wise cache or
run manifest that proves which historical PCA dependency/model state produced
its scores. The remaining residual is small on long data and nonzero on short
data, consistent with a detector/dependency or numerical-output difference,
not a metric-window failure.

## Required next action

Do not relax the threshold and do not start CDU. Obtain the official Sub-PCA
score cache or reconstruct the exact historical execution environment (commit,
`PCA.py`, NumPy/SciPy/scikit-learn versions, and runner) and rerun this same
three-sequence audit. R0 can pass only when every `abs_diff <= 1e-6`.

Output: `layer2_results/subpca_residual_audit.csv`.
