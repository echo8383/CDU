# Protocol v1 two-machine runbook

Status frozen on 2026-09-10. The goal is to parallelize formal controls without
running the same control on two hosts or mixing different signatures.

## Assignment

| Owner | Work | Output ownership |
|---|---|---|
| Primary machine | finish `independent_noise` | `protocol_v1_results/controls/independent_noise/` |
| Collaborator | all complementary alphas: `0, 0.25, 0.5, 1, 2` | the five `complementary_alpha_*` directories |
| Primary machine after merge | clean/resume regression and final acceptance | final verification/acceptance files |

The exact duplicate control is already complete on the primary machine. The
primary queue scheduler was stopped while its independent-noise Python worker
was left running, preventing it from automatically entering complementary work.

## What Git contains

Git contains code, frozen protocol/configuration, source mapping, manifest with
expected SHA-256 values, and this runbook. It does **not** contain the basis
cache or generated control checkpoints.

The collaborator needs only:

- the cloned repository at the specified commit;
- `layer2_results/basis_scores/` (350 NPZ files, about 1.7 GB);
- the completed shared baseline plus `FOLD_AUDIT.csv`, `SPLIT_MANIFEST.json`,
  and `RUN_SIGNATURE.json` under `protocol_v1_results/controls/`.

The collaborator does not need raw TSB-AD CSVs or any of the nine detector
score caches for complementary controls.

## Primary-machine export

Export the external assets to a new directory on a portable drive or cloud-sync
folder (the target must not already exist):

```powershell
cd D:\CSIES\TSAD\Onelier\CDU_starter_kit\cdu_kit
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\export_protocol_v1_collaborator_assets.ps1 -Destination E:\cdu_protocol_v1_assets
```

Share that asset directory separately from Git. Do not add it to Git or Git
LFS. The basis cache is already compressed NPZ data and is too large for normal
source control.

## Collaborator setup and validation

```powershell
git clone <REMOTE_URL> cdu_kit
cd cdu_kit
git checkout <COMMIT_FROM_PRIMARY>
pip install -r requirements.txt

# Copy the contents of cdu_protocol_v1_assets into this repository root,
# preserving layer2_results/ and protocol_v1_results/ paths.
python scripts\validate_workspace.py --verify-basis-hashes
```

Hash validation must pass before running. A run-signature mismatch is a hard
stop; never delete or rewrite `RUN_SIGNATURE.json` to bypass it.

## Collaborator command

```powershell
python -u scripts\run_protocol_v1_complementary_shard.py --alphas 0 0.25 0.5 1 2 2>&1 | Tee-Object protocol_v1_complementary.log
```

The runner checkpoints after each outer source. Running the same command after
an interruption resumes and skips completed source checkpoints.

## Returning results

After the command prints `COLLABORATOR COMPLEMENTARY SHARD COMPLETE`, return
these five directories, preserving their exact names:

```text
protocol_v1_results/controls/complementary_alpha_0p0/
protocol_v1_results/controls/complementary_alpha_0p25/
protocol_v1_results/controls/complementary_alpha_0p5/
protocol_v1_results/controls/complementary_alpha_1p0/
protocol_v1_results/controls/complementary_alpha_2p0/
```

Do not return or overwrite `shared_baseline`, `RUN_SIGNATURE.json`, or any
negative-control directory. The primary machine must verify all five directories
contain 23 source JSON checkpoints and 350 unique per-series rows before merge.

## Final primary-machine gate

Only after independent noise and all returned complementary outputs are complete:

```powershell
python -u scripts\verify_protocol_v1_resume_clean.py
python -u scripts\run_protocol_v1_controls.py --phase audit
```

The pilot remains blocked unless `CONTROL_ACCEPTANCE.md` reports GO.
