"""Consolidate symmetric-interface, reconstruction, residual-VUS and bridge evidence."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from evaluate_cdu_protocol_v1 import DETECTORS
from run_protocol_v1_controls import atomic_csv

ROOT = Path(__file__).resolve().parents[1]
SYM = ROOT / "protocol_basis_results/cap2048/drop_symmetric_rank"
CTRL = ROOT / "protocol_basis_results/cap2048/drop_symmetric_rank_controls"
DECOMP = ROOT / "protocol_score_decomposition/cap2048"
BRIDGE = ROOT / "protocol_basis_bridge/cap2048"
EVIDENCE = ROOT / "paper/evidence/score_decomposition"


def source_bootstrap(values):
    values = np.asarray(values, dtype=float)
    boot = values[np.random.default_rng(2024).integers(0, len(values), size=(10000, len(values)))].mean(axis=1)
    return float(np.quantile(boot, .025)), float(np.quantile(boot, .975))


def main():
    original = pd.read_csv(ROOT / "paper/evidence/fast_main/MAIN_RESULTS.csv").rename(columns={"Detector": "detector"})
    recon = pd.read_csv(DECOMP / "SUMMARY.csv")
    detector_rows = []
    for detector in DETECTORS:
        cdu = pd.read_csv(SYM / detector / "SUMMARY.csv").iloc[0]
        vus = pd.read_csv(DECOMP / "vus" / f"{detector}_SUMMARY.csv").iloc[0]
        detector_rows.append({"detector": detector, "symmetric_rank_CDU": cdu.CDU,
            "symmetric_rank_CDU_CI_low": cdu.CDU_CI_low,
            "symmetric_rank_CDU_CI_high": cdu.CDU_CI_high,
            "symmetric_rank_positive_sources": int(cdu.positive_sources),
            **{key: vus[key] for key in vus.index if key != "detector"}})
    detector = pd.DataFrame(detector_rows).merge(recon, on="detector").merge(
        original[["detector", "Raw_VUS", "Source_macro_Raw_VUS", "CDU"]].rename(
            columns={"CDU": "legacy_basis_Fast_CDU"}), on="detector")
    detector["symmetric_CDU_rank"] = detector.symmetric_rank_CDU.rank(ascending=False, method="min").astype(int)
    detector["raw_rank"] = detector.Raw_VUS.rank(ascending=False, method="min").astype(int)
    atomic_csv(detector, EVIDENCE / "DETECTOR_DECOMPOSITION_SUMMARY.csv")

    baseline = pd.concat([pd.read_csv(p) for p in sorted((SYM / "baseline/by_source").glob("*.csv"))], ignore_index=True)
    assert len(baseline) == baseline.series_id.nunique() == 350
    null = pd.read_csv(ROOT / "protocol_fast_results/shared_baseline/PER_SERIES.csv")[["series_id", "L_null"]]
    basis = baseline.merge(null, on="series_id", validate="one_to_one")
    basis["basis_utility"] = basis.L_null - basis.L_basis
    per_source = basis.groupby("source_dataset", as_index=False).agg(
        L_prior=("L_null", "mean"), L_basis=("L_basis", "mean"), basis_utility=("basis_utility", "mean"))
    lo, hi = source_bootstrap(per_source.basis_utility)
    basis_summary = pd.DataFrame([{"interface": "symmetric_rank", "L_prior": per_source.L_prior.mean(),
        "L_basis": per_source.L_basis.mean(), "basis_utility": per_source.basis_utility.mean(),
        "CI_low": lo, "CI_high": hi, "positive_sources": int((per_source.basis_utility > 0).sum()),
        "n_sources": len(per_source)}])
    atomic_csv(per_source, EVIDENCE / "SYMMETRIC_BASIS_PER_SOURCE.csv")
    atomic_csv(basis_summary, EVIDENCE / "SYMMETRIC_BASIS_SUMMARY.csv")

    control_rows = []
    for name in ("duplicate_Var96", "independent_noise", "complementary_alpha2"):
        row = pd.read_csv(CTRL / name / "SUMMARY.csv").iloc[0].to_dict()
        row["control"] = name
        control_rows.append(row)
    controls = pd.DataFrame(control_rows)
    atomic_csv(controls, EVIDENCE / "SYMMETRIC_CONTROL_SUMMARY.csv")
    bridge = pd.read_csv(BRIDGE / "SUMMARY.csv")
    atomic_csv(bridge, EVIDENCE / "SERIES_CV_BRIDGE_SUMMARY.csv")

    lines = ["# Symmetric-interface score decomposition", "",
        "All detector scores are frozen. Training uses at most 2048 label-independently sampled points per series; all test points are retained.", "",
        "## Basis utility", "", basis_summary.to_markdown(index=False), "",
        "## Detector reconstruction and residual behavior", "", detector.to_markdown(index=False), "",
        "## Matching controls", "", controls.to_markdown(index=False), "",
        "## Series-CV bridge", "", bridge.to_markdown(index=False), ""]
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "SCORE_DECOMPOSITION_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(basis_summary.to_string(index=False), flush=True)
    print(detector[["detector", "source_macro_R2", "source_macro_Spearman", "Raw_VUS",
                    "predicted_VUS_series_macro", "residual_VUS_series_macro",
                    "symmetric_rank_CDU"]].to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
