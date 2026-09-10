# CDU: Conditional Detector Utility for TSAD

This repository contains the reproducible code, frozen protocol, detector
wrappers, configurations, and lightweight reference artifacts for evaluating
whether a detector score adds held-out label-predictive information beyond a
declared low-complexity statistical basis.

The complete handover document is [CDU_PROJECT_ARCHITECTURE_AND_PLAN.md](CDU_PROJECT_ARCHITECTURE_AND_PLAN.md). The frozen primary research contract is [protocol_v1.md](protocol_v1.md).

## Repository boundary

Tracked: source code, protocol, source grouping, 350-series index, configs,
small difficulty tables, and audit reports.

Not tracked: raw TSB-AD-U data, basis-score cache, detector-score cache,
checkpoints, logs, model weights, and generated outputs. The local score/basis
cache is about 4 GB and must be transferred outside Git according to its data
and third-party licence terms.

## Fresh clone

```powershell
git clone <REMOTE_URL> cdu_kit
cd cdu_kit
conda create -n cdu python=3.12 -y
conda activate cdu
pip install -r requirements.txt
python scripts\validate_workspace.py
```

The validator reports exactly which external assets are absent. It does not
modify data or run models.

## Local layout expected by the evaluator

```text
cdu_kit/
  uni_vuspr.csv                         # tracked index
  source_groups.json                    # tracked 23-source mapping
  Datasets/TSB-AD-U/<350 CSV files>     # external; detector sweeps only
  layer2_results/
    basis_scores/<350 NPZ files>        # external; CDU feature basis
    poly_pinned_scores/<350 NPY files>  # external; POLY cache
    detector_scores/<Detector>/<350 NPY files>
  protocol_v1_results/                  # generated and ignored
```

The frozen detector labels are `SubPCA`, `POLY`, `MOMENT_FT`, `MOMENT_ZS`,
`M2N2`, `TranAD`, `TimesNet`, `FITS`, and `AnomalyTransformer`.

## Running Protocol v1

Protocol v1 consumes cached detector scores; it never retrains a detector.
Its formal controls must pass before a detector pilot or main result is run.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_protocol_v1_control_queue.ps1 -BaselinePid 0
```

The controls are source-level resumable. Read
`protocol_v1_results/controls/CONTROL_ACCEPTANCE.md` after completion.

## Running a detector sweep

Detector sweeps require a separately obtained pinned TSB-AD checkout at commit
`8b363e350ae047a8115a594d1e9da64aae09b852`. Set its location explicitly:

```powershell
$env:TSB_AD_ROOT = 'D:\repos\TSB-AD'
python scripts\run_detector_smoke.py --detector TranAD --seed 2024
python scripts\run_detector_sweep.py --detector TranAD --seed 2024 --resume
```

The sweep saves one curve and updates its manifest after each series. Do not
overwrite an audited cache in place; write a new cache/branch and record why.

## Collaboration rules

- Never commit datasets, score caches, checkpoints, API tokens, or model weights.
- Do not alter the 31 basis, source groups, folds, probe grid, rank transform,
  aggregation, or bootstrap after inspecting Protocol v1 outcomes.
- Preserve AnomalyTransformer collapsed curves; constant scores map to 0.5.
- Stage-2 authority is `STAGE2_FULL_AUDIT_REPORT.md`; it is not the Protocol v1
  paper result table.
- Historical leaderboard VUS values must never be mixed with pinned-cache or
  Protocol v1 results.

## Useful entry points

| Task | Command/file |
|---|---|
| Validate assets | `python scripts/validate_workspace.py` |
| Build source mapping | `python scripts/build_source_groups.py` |
| Audit folds | `python scripts/audit_protocol_v1_folds.py` |
| Resume formal controls | `scripts/run_protocol_v1_control_queue.ps1` |
| Protocol evaluator | `scripts/evaluate_cdu_protocol_v1.py` |
| Detector smoke test | `scripts/run_detector_smoke.py` |
| Resumable detector sweep | `scripts/run_detector_sweep.py` |
| Project handover | `CDU_PROJECT_ARCHITECTURE_AND_PLAN.md` |
