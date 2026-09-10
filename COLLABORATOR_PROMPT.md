# Task: run the Protocol v1 complementary-control shard

You are helping execute one isolated part of a frozen CDU evaluation protocol.
Do not redesign the method or run any detector.

## Repository and assets

1. Clone the repository URL supplied by the primary researcher and use the exact
   requested commit/branch.
2. Separately obtain the `cdu_protocol_v1_assets` directory from the primary
   researcher. It is not stored in Git.
3. Copy the asset directory contents into the clone root, preserving these paths:

```text
layer2_results/basis_scores/
protocol_v1_results/controls/shared_baseline/
protocol_v1_results/controls/FOLD_AUDIT.csv
protocol_v1_results/controls/SPLIT_MANIFEST.json
protocol_v1_results/controls/RUN_SIGNATURE.json
```

## Scope

Run only the five frozen complementary controls:

```text
alpha = 0, 0.25, 0.5, 1, 2
S_alpha = Z + alpha * Y
```

These are evaluator calibration controls, not detectors. Do not run duplicate,
noise, pilot detectors, nine-detector evaluation, Stage 3, Raw VUS, or hard-VUS.

Do not modify:

- `protocol_v1.md`;
- `source_groups.json`;
- `protocol_v1_input_manifest.json`;
- `scripts/evaluate_cdu_protocol_v1.py`;
- `scripts/run_protocol_v1_controls.py`;
- basis cache contents;
- split, seed, probe, C grid, weighting, aggregation, or output definitions.

Do not delete or bypass `RUN_SIGNATURE.json`. A signature mismatch is a STOP.

## Setup and mandatory validation

```powershell
cd <CLONED_CDU_KIT>
python --version
pip install -r requirements.txt
python scripts\validate_workspace.py --verify-basis-hashes
```

The validator must show:

- benchmark index: PASS;
- 350-series cardinality: PASS;
- source map and coverage: PASS;
- frozen protocol: PASS;
- basis cache: 350/350;
- basis SHA-256 mismatches: 0.

Raw TSB-AD-U data, detector score caches, and `TSB_AD_ROOT` are not required for
this task. Their `MISSING` status is acceptable.

## Run command

```powershell
python -u scripts\run_protocol_v1_complementary_shard.py --alphas 0 0.25 0.5 1 2 2>&1 | Tee-Object protocol_v1_complementary.log
```

The task is resumable at the outer-source level. If interrupted, run exactly the
same command again; completed source checkpoints will be skipped.

## Required completion checks

For every directory below, require 23 `by_source/*.json` checkpoints and a
350-row unique-series aggregate CSV:

```text
protocol_v1_results/controls/complementary_alpha_0p0/
protocol_v1_results/controls/complementary_alpha_0p25/
protocol_v1_results/controls/complementary_alpha_0p5/
protocol_v1_results/controls/complementary_alpha_1p0/
protocol_v1_results/controls/complementary_alpha_2p0/
```

Do not interpret or tune results. Report failures exactly as produced.

## Return to the primary researcher

Return:

1. the five complementary result directories above;
2. `protocol_v1_complementary.log`;
3. output of `git rev-parse HEAD`;
4. Python, NumPy, pandas, SciPy, and scikit-learn versions;
5. a short statement listing which alpha controls completed 23/23.

Do not return or overwrite the primary machine's shared baseline, duplicate, or
independent-noise results. The primary researcher will merge the five disjoint
directories and run the final clean/resume and acceptance checks.
