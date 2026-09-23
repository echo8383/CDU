# Follow-up experiments fixed on 2026-09-17

These are follow-ups after inspecting linear/spline/HGB results, not a retrospective preregistration.
Use all nine frozen detector score caches. No detector fitting or performance-dependent exclusions.

1. Metric control: detector-only prediction for linear, spline, HGB, matched to the existing sample indices,
   source folds, weights, probe settings and full test curves. Compute a sampled-training null prior
   using only training labels. Join existing basis and basis+detector losses by series ID.
2. Seed sensitivity: original matched sample is replicate 0; run spline replicates 1--4.
   Hash `rank-probe-matched-v1|replicate=N|series_id` for sampling. Total five replicates;
   model seed remains 2024. Each new replicate fits one shared baseline and all nine detector probes.
3. Basis sensitivity: spline, original replicate-0 sampling; drop each of the seven predefined families.
   Each variant uses its own shared baseline and all nine detectors. Compare to original spline full basis.
4. Statistical sensitivity: jointly resample saved source increments across 27 detector/probe combinations;
   report simultaneous intervals within nine and across 27, plus explicitly exploratory source t-test/Holm
   results. Shared training-set dependence is not removed by these calculations. Source deletion means
   leave-one-source-out aggregation of existing losses, not refitting.

Training cap 2048, all test timestamps. No new control fitting is claimed for seed/ablation variants;
the primary matched controls remain separately reported. Outcomes will not be used to choose a favorable
seed, basis variant or probe. Existing results are preserved.

Three independent queues (`metric`, `seeds`, `basis`) execute sequentially within each track,
save a checkpoint after every source, and continue to the next configuration if one fails.
Failures remain visible and the queue exits unsuccessfully when any job failed.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/queue_cdu_followup.ps1 -Track metric
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/queue_cdu_followup.ps1 -Track seeds
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/queue_cdu_followup.ps1 -Track basis
```

Outputs: `protocol_followup_results/`. Lightweight inference:
`paper/evidence/source_inference/`. Raw losses remain available, including detector-only losses.
