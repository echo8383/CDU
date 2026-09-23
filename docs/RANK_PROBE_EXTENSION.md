# Matched probe extension

Run started 2026-09-17. This experiment tests whether conditional utility depends
on linear probe capacity. It uses all nine frozen detectors and 23-source LOSO.

## Fixed settings

- Basis and detector features: within-series average ranks; ties share ranks.
- Training: at most 2048 uniformly sampled timestamps per series, seed derived
  from `rank-probe-matched-v1|series_id`. Identical indices for all three probes.
- Testing: every timestamp. Source-macro mean of per-series mean log loss, bits.
- Linear: existing logistic probe, C=0.1.
- Spline: additive cubic splines, four fixed knots at 0, 1/3, 2/3, 1;
  omit redundant spline bias; same logistic probe and C.
- HGB: existing fixed 32-iteration, depth-3, seven-leaf configuration.
- Each probe: shared basis baseline, duplicate Var-96, independent noise,
  synthetic noise+2Y calibration, then the nine detectors.
- Uncertainty: 10,000 paired source resamples, seed 2024.
- No result-dependent hyperparameter selection. Controls and unfavorable
  detector results are reported with the same settings.

These are matched sampled-training robustness experiments. They are not
full-training reruns. Synthetic label injection is used only in its explicitly
named calibration control.

## Run and resume

```powershell
python -u scripts/run_rank_probe_extension.py --probe linear --resume
python -u scripts/run_rank_probe_extension.py --probe spline --resume
python -u scripts/run_rank_probe_extension.py --probe hgb --resume
```

Outputs: `protocol_rank_probe_results/cap2048/<probe>/<condition>/`.
Each source writes a CSV and metadata checkpoint. Each completed condition
writes per-series, per-source and summary CSVs. A successful complete run writes
`QUEUE_STATUS.json`. Logs for the launched jobs are in
`protocol_rank_probe_results/logs/`.

The previous symmetric-rank runs use different sampling seeds across their
wrappers. Use this extension's matched linear results when comparing spline
and HGB, rather than attributing sampling differences to probe capacity.
