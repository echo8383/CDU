"""Validate and consolidate completed normalization/reference-strength runs."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from evaluate_cdu_protocol_v1 import DETECTORS

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "protocol_reference_robustness"
OUT = ROOT / "paper" / "evidence" / "reference_robustness"
PRIMARY = pd.read_csv(ROOT / "paper/evidence/rank_probe_extension/DETECTORS.csv")
PRIMARY = PRIMARY[PRIMARY.probe == "spline"].set_index("detector")


def load_variant(experiment: str, variant: str) -> pd.DataFrame | None:
    rows = []
    for detector in DETECTORS:
        path = RUNS / experiment / "cap2048" / variant / detector / "SUMMARY.csv"
        if not path.exists():
            return None
        row = pd.read_csv(path).iloc[0].to_dict()
        row.update(experiment=experiment, variant=variant, detector=detector)
        rows.append(row)
    frame = pd.DataFrame(rows)
    if set(frame.detector) != set(DETECTORS) or not np.isfinite(frame.CDU).all():
        raise RuntimeError(f"Invalid completed variant: {experiment}/{variant}")
    frame["CDU_rank"] = frame.CDU.rank(ascending=False, method="min").astype(int)
    return frame


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frames = []
    stability = []
    primary = PRIMARY.CDU.reindex(DETECTORS)
    for experiment, variants in {
        "normalization": ("minmax", "zscore_cdf"),
        "strength": ("variance", "variance_range", "local_deviation", "dispersion_change"),
    }.items():
        for variant in variants:
            frame = load_variant(experiment, variant)
            if frame is None:
                print(f"[{experiment}/{variant}] INCOMPLETE", flush=True)
                continue
            aligned = frame.set_index("detector").CDU.reindex(DETECTORS)
            rho = float(spearmanr(primary, aligned).statistic)
            stability.append({"experiment": experiment, "variant": variant,
                              "rho_vs_primary_spline": rho,
                              "max_abs_CDU_change": float(np.max(np.abs(primary - aligned))),
                              "top2_same": set(aligned.nlargest(2).index) == set(primary.nlargest(2).index),
                              "top4_same": set(aligned.nlargest(4).index) == set(primary.nlargest(4).index)})
            frames.append(frame)
            print(f"[{experiment}/{variant}] COMPLETE rho={rho:.3f}", flush=True)
    if frames:
        pd.concat(frames, ignore_index=True).to_csv(OUT / "DETECTORS.csv", index=False)
    pd.DataFrame(stability).to_csv(OUT / "STABILITY.csv", index=False)
    print(pd.DataFrame(stability).to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
