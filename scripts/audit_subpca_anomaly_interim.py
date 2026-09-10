"""Lightweight parallel audit while the POLY full audit is running.

Deliberately excludes the expensive all-series VUS/CDU recalculation.  It
checks the two remaining detector caches, point-wise alignment, manifest hash
parity, and the fixed three-series reproducibility sample.
"""
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_three_detectors import integrity, reproducibility  # noqa: E402

L2 = ROOT / "layer2_results"
OUT = L2 / "audit_interim_subpca_anomaly.csv"
REPORT = ROOT / "SUBPCA_ANOMALY_INTERIM_AUDIT.md"


def main():
    all_rows = []
    rep_rows = []
    for detector in ("SubPCA", "AnomalyTransformer"):
        print(f"[{detector}] integrity 1/2", flush=True)
        frame = integrity(detector)
        frame["interim_stage"] = "cache_integrity_alignment"
        all_rows.append(frame)
        print(f"[{detector}] reproducibility 2/2", flush=True)
        rep_rows.append(reproducibility(detector))
        print(f"[{detector}] interim audit PASS-CANDIDATE", flush=True)

    integrity_df = pd.concat(all_rows, ignore_index=True)
    repro_df = pd.concat(rep_rows, ignore_index=True)
    summary = []
    for detector in ("SubPCA", "AnomalyTransformer"):
        a = integrity_df[integrity_df.detector == detector]
        r = repro_df[repro_df.detector == detector]
        summary.append({
            "detector": detector,
            "series": len(a),
            "length_alignment_pass": bool(a.score_label_alignment.eq("PASS").all()),
            "basis_label_alignment_pass": bool(a.basis_label_match.all()),
            "finite_ratio_all_one": bool(a.finite_ratio.eq(1.0).all()),
            "any_constant_score": bool(a.constant_score.any()),
            "manifest_hash_match": bool(a.manifest_hash_match.all()),
            "repro_samples_hash_match": bool(r.hash_match_runs.all() and r.hash_match_cache.all()),
            "full_VUS_CDU_recompute": "PENDING (POLY audit continues first)",
        })
    result = pd.DataFrame(summary)
    integrity_df.to_csv(OUT, index=False)
    repro_df.to_csv(L2 / "audit_interim_subpca_anomaly_repro.csv", index=False)
    REPORT.write_text(
        "# SubPCA / AnomalyTransformer interim audit\n\n"
        "This is a parallel lightweight audit only: score cache integrity, score-label-basis alignment, manifest hash parity, and three-series fixed-seed reproducibility. "
        "It intentionally does not recompute full VUS or CDU while the POLY full recomputation is occupying memory.\n\n"
        + result.to_markdown(index=False) + "\n",
        encoding="utf-8",
    )
    print(result.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
