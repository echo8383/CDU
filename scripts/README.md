# Script index

Choose a command by what you need. Paper assembly and checks read the small tracked `paper/evidence/` snapshots; score-level analysis requires external ignored caches.

| Task | Entry point | Detector rerun? |
|---|---|---|
| Verify numbers cited in current manuscript | `validate_story_claims.py` | No |
| Regenerate current table and figures from saved evidence | `prepare_submission_assets.py` | No |
| Check external dataset and cache placement | `validate_workspace.py` | No |
| Build ranked basis curves | `build_ranked_basis_cache.py` | No; basis cache required |
| Primary rank/probe extension and controls | `run_rank_probe_extension.py` | No; frozen score caches required |
| Probe / basis / reference sensitivity | `run_probe_robustness.py`, `run_basis_sensitivity.py`, `run_reference_robustness.py` | No; caches required |
| Score reconstructability | `run_score_decomposition.py` | No; caches required |
| Historical fixed-C source-LOSO run | `run_protocol_fast.py` | No; caches required |
| Optional detector smoke / score sweep | `run_detector_smoke.py`, `run_detector_sweep.py` | **Yes** |

The current English and Chinese manuscripts are built with `icassp/build.ps1` and `icassp/build_zh.ps1`. Earlier generators such as `render_paper_figures.py` and `prepare_paper_revision.py` are kept for provenance; they are **not** the current submission-asset entry point. PowerShell queue scripts are local run orchestration, not required to read or build the paper.

Generated `protocol_*_results/`, `layer2_results/`, logs, and temporary files are intentionally ignored. Publish only selected result snapshots via `paper/evidence/`; do not `git add -f` entire run directories.
