# Active scripts

| Script | Purpose |
|---|---|
| `run_protocol_fast.py` | Primary fixed-C source-LOSO baseline and detector evaluation |
| `validate_workspace.py` | Check tracked metadata and external cache availability |
| `evaluate_cdu_protocol_v1.py` | Shared feature, weighting and loss primitives |
| `run_protocol_v1_controls.py` | Shared cache-loading and atomic-output primitives |
| `build_source_groups.py` | Rebuild the frozen source map if auditing inputs |
| `build_protocol_v1_input_manifest.py` | Rebuild input metadata if auditing inputs |
| `run_detector_smoke.py` | Optional detector wrapper smoke test |
| `run_detector_sweep.py` | Optional point-score cache generation |
| `recompute_raw_vus_cache_only.py` | Cache-only Raw VUS calculation |

The paper main run uses only `run_protocol_fast.py`. The older experimental,
audit, R0, Stage-2 and Stage-3 scripts are preserved by Git tag
`archive/pre-paper-cleanup-2026-09-14` rather than exposed as active entry
points.

