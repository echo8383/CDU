# Reproducing CDU

Run all commands from the repository root. Python 3.11 with `requirements.txt` is the recommended analysis environment. This guide concerns the frozen-score evaluation; training the original detectors is a separate workflow.

## 1. Inspect and validate the paper results

```bash
python -m pip install -r requirements.txt
python scripts/validate_story_claims.py
```

This uses only tracked `paper/evidence/` files and checks matched-metric ranks, paired contrasts, reconstruction, seed and reference sensitivity. The authoritative primary CDU evidence is `paper/evidence/rank_probe_extension/`, with detector-only utility in `paper/evidence/cdu_followup/`. `fast_main/` supplies the benchmark Raw VUS column; its older CDU values are not the primary spline results.

To rebuild the table and quantitative figures from saved evidence, optionally run `python scripts/prepare_submission_assets.py`. This overwrites generated assets; the checked-in PDF assets preserve the frozen submission layout. The author-drawn main diagram is supplied as `icassp/figures/main_concept.drawio` and PDF.

## 2. Build the paper

Install a LaTeX distribution containing pdfLaTeX and BibTeX. On Linux:

```bash
cd icassp
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

Windows, from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File icassp/build.ps1
```

`icassp/main.pdf` is the English submission. The Chinese edition is an older reading version.

## 3. Inputs for independent probe reruns

The 350 series identifiers and 23 source groups are frozen in `source_groups.json`. Identifiers include `.csv`; do not strip that suffix from cache filenames.

```text
layer2_results/
  basis_scores/<series_id>.npz
  poly_pinned_scores/<series_id>.npy
  detector_scores/SubPCA/<series_id>.npy
  detector_scores/MOMENT_FT/<series_id>.npy
  detector_scores/MOMENT_ZS/<series_id>.npy
  detector_scores/M2N2/<series_id>.npy
  detector_scores/TranAD/<series_id>.npy
  detector_scores/TimesNet/<series_id>.npy
  detector_scores/FITS/<series_id>.npy
  detector_scores/AnomalyTransformer/<series_id>.npy
```

Each NPZ contains `basis` (31 x T), `label` (T binary labels), and `names` (31 feature names in matching row order). Each detector NPY is a finite one-dimensional array of length T, aligned point-for-point with those labels. Preserve constant/collapsed curves. Raw benchmark CSVs are unnecessary for this cached-score CDU run because labels reside in the basis cache. Raw VUS recomputation and detector sweeps require the separate benchmark/metric dependencies.

These large inputs are ignored by Git and are not currently published as a downloadable release. Obtain the frozen bundle from the authors via a repository issue. `protocol_v1_input_manifest.json` records input provenance; do not substitute newly generated scores and describe them as the original frozen detector instances. Raw benchmark access is provided by https://github.com/TheDatumOrg/TSB-AD under its own terms.

## 4. Prepare ranked basis and controls

```bash
python scripts/validate_workspace.py
python -u scripts/build_ranked_basis_cache.py --resume
python -c "import sys; sys.path.insert(0, 'scripts'); from run_symmetric_rank_controls import build_controls; build_controls()"
```

The workspace validator also reports optional detector-training inputs; missing raw data or TSB_AD_ROOT does not block cached-score CDU when the basis and relevant detector caches are present. Preparation ranks every basis curve independently, preserves average ties, and maps constant curves to 0.5. The three controls are duplicate Var-96, independent noise and label-informed synthetic Z+2Y. The synthetic control is calibration only.

## 5. Primary experiment and probe sensitivity

```bash
python -u scripts/run_rank_probe_extension.py --probe spline --training-cap 2048 --threads 2 --resume
python -u scripts/run_rank_probe_extension.py --probe linear --training-cap 2048 --threads 2 --resume
python -u scripts/run_rank_probe_extension.py --probe hgb --training-cap 2048 --threads 2 --resume
python scripts/summarize_rank_probe_extension.py
```

Each run evaluates the baseline, three controls and all nine detectors over 23 source-held-out folds. Training retains up to 2048 label-independently sampled points per series; testing retains all points. Source/series weights and source-macro loss aggregation are shared. Spline logistic is the primary probe (C=0.1, cubic splines, four fixed knots); linear and HGB are sensitivity checks. The final protocol uses fixed settings, not the historical inner-grid-search protocol.

Outputs/checkpoints are under `protocol_rank_probe_results/cap2048/<probe>/`. For a bounded smoke run add `--max-new-folds 1`. Resume skips completed folds. Resume signatures include code, input metadata and timestamps: copying inputs or changing code can invalidate an existing run. On another machine start fresh outputs; preserve old outputs rather than bypassing signature checks. Reruns need CPU/RAM, not a GPU; runtime depends on hardware. Start one probe at a time.

## 6. Matched standalone comparison and reconstruction

After the corresponding primary probe completes:

```bash
python -u scripts/run_cdu_followup.py --mode detector_only --probe spline --threads 2 --resume
python -u scripts/run_cdu_followup.py --mode detector_only --probe linear --threads 2 --resume
python -u scripts/run_cdu_followup.py --mode detector_only --probe hgb --threads 2 --resume
python -u scripts/run_score_decomposition.py
```

Additional seed/basis commands are exposed by `python scripts/run_cdu_followup.py --help`; reference-strength and score-interface options by `python scripts/run_reference_robustness.py --help`. Definitions and evidence locations are documented in `paper/reports/TECHNICAL_METHODS.md` and `paper/evidence/README.md`. Do not replace the frozen evidence with partial rerun outputs.

## Interpretation

CDU is paired held-out basis-only minus basis-plus-detector log-loss, in bits. Negative finite-sample estimates are retained. Intervals resample source groups, not timestamps. Standalone accuracy, score reconstruction and conditional contribution answer different questions. No detector training or historical leaderboard matching is performed by these evaluation commands.
