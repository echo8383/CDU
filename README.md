# CDU: Beyond-basis evaluation for time-series anomaly detection

This repository evaluates how much label-relevant predictive information a
time-series anomaly detector score adds beyond a declared 31-dimensional
low-complexity statistical basis.

The deadline-focused paper protocol is intentionally small:

- 350 cached TSB-AD-U series;
- 23-source leave-one-source-out evaluation;
- one globally fixed L2 logistic probe (`C=0.1`);
- four held-out losses: null, basis, detector, and basis+detector;
- source-macro aggregation and paired source bootstrap;
- nine frozen detector score caches; detectors are not rerun.

Read [the active protocol](docs/PROTOCOL.md) and
[the experiment map](docs/EXPERIMENTS.md) before running anything.

## Repository layout

```text
cdu_kit/
docs/                    # Active protocol and compact reference material
paper/icassp2027/        # Four-page paper source
scripts/                 # Active command-line entry points
wrappers/                # Detector-to-point-score adapters
configs/                 # Pinned detector configurations
data/                    # Small tracked analysis tables
layer2_results/          # External caches; generated/ignored
protocol_fast_results/   # Active main-run outputs; generated/ignored
protocol_v1_results/     # Historical exhaustive controls; generated/ignored
source_groups.json       # Frozen 350-series to 23-source mapping
protocol_v1_input_manifest.json
uni_vuspr.csv            # Frozen benchmark index
requirements.txt
```

Legacy scripts and reports were removed from the active branch on 2026-09-14.
They remain available at Git tag:

```text
archive/pre-paper-cleanup-2026-09-14
```

Local copies may also exist under ignored `_archive/`.

## Install

```bash
python -m pip install -r requirements.txt
```

Only NumPy, pandas, SciPy and scikit-learn are required for cached-score CDU
evaluation. Detector training dependencies are unnecessary for the main run.

## Validate external assets

```bash
python scripts/validate_workspace.py --verify-basis-hashes
python scripts/run_protocol_fast.py --detectors TranAD TimesNet FITS --dry-run
```

## Run the paper experiment

One command computes the fixed-C shared baseline and then evaluates an assigned
detector shard. All completed source checkpoints are skipped on restart.

```bash
python -u scripts/run_protocol_fast.py \
  --baseline \
  --detectors TranAD TimesNet FITS \
  --resume \
  --continue-on-error
```

The three-machine assignment is:

| Worker | Detectors |
|---|---|
| Primary | SubPCA, POLY, MOMENT_FT |
| Collaborator | AnomalyTransformer, MOMENT_ZS, M2N2 |
| AutoDL | TranAD, TimesNet, FITS |

Outputs are written to `protocol_fast_results/main/<Detector>/` as
`PER_SERIES.csv`, `PER_SOURCE.csv`, `SUMMARY.csv`, and 23 resumable source
checkpoints.

## External artifacts

Git intentionally excludes raw data, basis caches, detector score caches,
checkpoints, logs, and generated results. A main-run worker needs only:

- `layer2_results/basis_scores/`;
- its assigned `layer2_results/detector_scores/<Detector>/` directories;
- tracked index/mapping/manifest files.

POLY uses `layer2_results/poly_pinned_scores/`.

## Historical evidence

The exhaustive nested-CV controls and Stage-2 audits remain evidence, but are
not recomputed for the fast main run. The compact Stage-2 reference is kept at
[docs/reference/STAGE2_AUDIT.md](docs/reference/STAGE2_AUDIT.md).
