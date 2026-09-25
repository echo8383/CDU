# CDU: beyond-basis evaluation of time-series anomaly scores

Code for **Beyond Standalone Performance: What Do Time-Series Anomaly Detectors Add Beyond Simple Statistics?**

Repository: https://github.com/echo8383/CDU

## Quick start (fresh checkout)

Use Python 3.11 and run commands from the repository root. No GPU or detector training is required for the offline evaluation.

```bash
git clone https://github.com/echo8383/CDU.git
cd CDU
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/validate_story_claims.py
```

The last command checks the tracked numerical evidence used in the paper. It does not retrain probes. For complete score-level reruns, input formats, controls, primary spline and sensitivity commands, see **[docs/REPRODUCING.md](docs/REPRODUCING.md)**.

**Input availability:** this checkout includes the source map, curated results, analysis code and paper assets. Point-wise score/basis caches are not included and currently have no public download in this repository. Full evaluation therefore requires those external inputs; request the frozen cache bundle through a repository issue. The instructions below distinguish this requirement from evidence-only reproduction.

This is the shareable code, manuscript, metadata, and **curated result evidence** for a 350-series TSB-AD-U study. It asks how much label-relevant predictive utility a frozen detector score contributes beyond a declared 31-score statistical reference. The current paper uses source-held-out evaluation and reports spline as its primary probe, with linear and HGB sensitivity analyses. Older fixed-C and Stage-2 results are retained as historical evidence, not silently mixed into the current paper.

## Start here

| Goal | Location / command |
|---|---|
| Read the paper | [`icassp/main.pdf`](icassp/main.pdf), source [`icassp/main.tex`](icassp/main.tex) |
| Read the Chinese edition | [`icassp/main_zh.pdf`](icassp/main_zh.pdf) |
| Inspect reported numbers | [`paper/evidence/README.md`](paper/evidence/README.md) |
| Understand the experiments | [`paper/README.md`](paper/README.md), [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) |
| Check numerical claims without score caches | `python scripts/validate_story_claims.py` |
| Rebuild figures and table from saved evidence | `python scripts/prepare_submission_assets.py` |

## Repository map

```text
icassp/             Current EN/ZH manuscript, required figure PDFs and final PDFs
paper/evidence/      Small, frozen CSV/JSON results used by the manuscript
paper/reports/       Detailed analyses and provenance notes
docs/                Protocol history and experiment documentation
scripts/             Analysis, validation and optional reproduction entry points
cdu/ wrappers/       Evaluation compatibility code and detector adapters
configs/             Pinned detector and probe configurations
data/                Small tracked difficulty / reproducibility metadata
source_groups.json   Frozen 350-series to 23-source mapping
uni_vuspr.csv        Frozen 350-series benchmark index
protocol_v1_input_manifest.json  Input provenance and hashes
```

Large local inputs and run outputs are **not in Git**: `Datasets/`, `layer2_results/`, `protocol_*_results/`, `tmp/`, and `_archive/`. They remain in place on the original machine so existing scripts and checkpoints are not broken. The `paper/evidence/` snapshots are intentionally tracked; they are the compact, reviewable results, not raw detector-score caches. No detector needs to be rerun to inspect the paper.

## Reproduce at two levels

For a paper-only checkout, install the light analysis dependencies and check the frozen numbers:

```bash
python -m pip install -r requirements.txt
python scripts/validate_story_claims.py
python scripts/prepare_submission_assets.py
```

Build the English manuscript with `powershell -NoProfile -ExecutionPolicy Bypass -File icassp/build.ps1` on Windows, or run `pdflatex`/`bibtex` on `icassp/main.tex` on Linux. The repository also includes a prebuilt PDF for quick review.

Full score-level reproduction additionally requires the separately distributed 350 raw series, the 31 basis curves in `layer2_results/basis_scores/`, and the nine frozen detector-score directories in `layer2_results/detector_scores/` (POLY uses `layer2_results/poly_pinned_scores/`). Check placement with `python scripts/validate_workspace.py`. These inputs are too large and/or separately licensed for the Git repository. See [`scripts/README.md`](scripts/README.md) before running any analysis; do not infer that the historical `docs/PROTOCOL.md` fixed-C configuration is the manuscript's current primary probe.

The ignored `_archive/` contains recoverable local legacy manuscript components. Nothing in the current `icassp/main.tex` or `icassp/main_zh.tex` depends on them. Git history also preserves the earlier project state.
