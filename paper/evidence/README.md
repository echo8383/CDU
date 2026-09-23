# Curated evidence included in Git

This directory is the small, shareable result layer behind `icassp/main.tex`. It is **not** a detector-score cache and contains no raw TSB-AD series. The current paper's tables/figures are assembled by `scripts/prepare_submission_assets.py` and checked by `scripts/validate_story_claims.py`.

| Directory | Role |
|---|---|
| `fast_main/` | Frozen nine-detector source-LOSO fixed-C results and per-source/per-series losses; benchmark Raw VUS reference |
| `fast_controls/` | Formal duplicate/noise/complementary controls and fold audit |
| `rank_probe_extension/` | Symmetric rank-interface linear, spline, and HGB results and controls; **current primary spline CDU table** |
| `cdu_followup/` | Matched detector-only utility, five-seed and basis-family sensitivity |
| `score_decomposition/` | Source-held-out reconstruction of detector scores from the statistical basis |
| `reference_robustness/` | Reference-strength and normalization sensitivity |
| `paired_contrasts/`, `source_inference/` | Paired comparisons and source-level inference diagnostics |
| `probe_robustness/`, `basis_sensitivity/` | Additional probe and reference sensitivity |
| `2026-09-14/`, `2026-09-15/` | Dated **historical** status snapshots; not current authoritative results |

The main table intentionally combines benchmark-standard Raw VUS with the explicitly labeled current spline CDU estimate. Those quantities have different evaluation meanings; do not substitute historical Stage-2 CDU or older fixed-C values for the spline rows. See `paper/reports/TECHNICAL_METHODS.md` and `paper/reports/REFERENCE_ROBUSTNESS_20260923.md` for methods and provenance.

Files here are selected CSV/JSON/Markdown summaries. Full point-wise basis/detector scores, raw datasets and resumable experiment checkpoints stay outside Git under the ignored local run directories. Any new paper number should be copied into a named evidence subdirectory with its provenance and validated before citation.
