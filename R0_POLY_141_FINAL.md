# R0 POLY-141 final report

1. **Where did official VUS `0.927581382367` come from?**

   It comes from the `POLY` column of
   `benchmark_exp/benchmark_eval_results/uni_mergedTable_VUS-PR.csv`, keyed by
   `141_MSL_id_2_Sensor_tr_500_1st_550.csv`, committed in leaderboard update
   `887a360aa1cd65fe9a93df0b614e9734b91a4917`. The artifact is a merged
   historical result; no corresponding POLY point-score cache or runner log is
   available locally.

2. **What exact difference causes `0.699803801586`?**

   Current `POLY.fit` (commit `8b363e3`) applies min-max input normalization
   (`normalize=True`). The historical implementation before commit `f2bf6b3`
   did not normalize. Holding raw input, power 4, periodicity 1, and window
   264 fixed, the no-normalization reconstruction yields the official value;
   the normalized reconstruction yields `0.699803801586`. The discrepancy is
   deterministic and is not due to the window, labels, length, NaNs, or VUS
   numerical integration.

3. **Can the official result be reproduced?**

   **Yes,** with the historically justified pre-`f2bf6b3` POLY implementation
   (`normalize=False`), official HP `power=4`, raw input, and historical window
   compatibility. The reproduced value differs by `3.33e-16`.

4. **Is POLY allowed to continue full R0 screening?**

   **Not with the current runner.** POLY remains R0 FAIL until the runner is
   explicitly switched to the historically justified no-normalization mode and
   that compatibility path is separately audited. No CDU was run.

## Required gate status

The single-sequence provenance audit is resolved, but the 350-series R0 gate is
not yet passed. Sequence 141 must not be excluded, and the `1e-6` threshold is
unchanged.
