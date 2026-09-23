"""Read-only summary of completed CDU follow-up experiments."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper/evidence/cdu_followup"
DETECTORS = ["SubPCA", "POLY", "MOMENT_FT", "MOMENT_ZS", "M2N2", "TranAD",
             "TimesNet", "FITS", "AnomalyTransformer"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    metric = []
    for probe in ("linear", "spline", "hgb"):
        for detector in DETECTORS:
            frame = pd.read_csv(ROOT / "protocol_followup_results" /
                                f"detector_only_{probe}_seed0" / detector / "PER_SERIES.csv")
            source = frame.groupby("source_dataset")[["detector_utility", "CDU"]].mean()
            metric.append({"probe": probe, "detector": detector,
                           "detector_utility": source.detector_utility.mean(),
                           "CDU": source.CDU.mean()})
    metric = pd.DataFrame(metric)
    metric.to_csv(OUT / "DETECTOR_ONLY_VS_CDU.csv", index=False)
    corr = []
    for probe, group in metric.groupby("probe"):
        corr.append({"probe": probe,
                     "spearman_detector_utility_vs_CDU":
                     spearmanr(group.detector_utility, group.CDU).statistic})
    pd.DataFrame(corr).to_csv(OUT / "METRIC_RANK_CORRELATION.csv", index=False)

    seed_rows = []
    for seed in range(5):
        base = (ROOT / "protocol_rank_probe_results/cap2048/spline" if seed == 0 else
                ROOT / "protocol_followup_results" / f"seed_spline_seed{seed}")
        for detector in DETECTORS:
            row = pd.read_csv(base / detector / "SUMMARY.csv").iloc[0]
            seed_rows.append({"seed": seed, "detector": detector, "CDU": row.CDU,
                              "CI_low": row.CDU_CI_low, "CI_high": row.CDU_CI_high})
    seeds = pd.DataFrame(seed_rows)
    seeds.to_csv(OUT / "SPLINE_FIVE_SEEDS.csv", index=False)
    seed_summary = seeds.groupby("detector").agg(
        mean=("CDU", "mean"), sd=("CDU", "std"), minimum=("CDU", "min"),
        maximum=("CDU", "max"), positive_seeds=("CDU", lambda x: int((x > 0).sum())),
        ci_positive_seeds=("CI_low", lambda x: int((x > 0).sum()))).loc[DETECTORS]
    seed_summary.to_csv(OUT / "SPLINE_FIVE_SEED_SUMMARY.csv")
    seeds.pivot(index="detector", columns="seed", values="CDU").corr(method="spearman").to_csv(
        OUT / "SPLINE_SEED_RANK_CORRELATION.csv")

    original = pd.Series({detector: pd.read_csv(
        ROOT / "protocol_rank_probe_results/cap2048/spline" / detector / "SUMMARY.csv").iloc[0].CDU
        for detector in DETECTORS})
    basis_rows = []
    for folder in sorted((ROOT / "protocol_followup_results").glob("basis_spline_seed0_*")):
        if not (folder / "QUEUE_STATUS.json").exists():
            continue
        values = pd.Series({detector: pd.read_csv(folder / detector / "SUMMARY.csv").iloc[0].CDU
                            for detector in DETECTORS})
        basis_rows.append({"variant": folder.name,
                           "rho_vs_full": spearmanr(original, values).statistic,
                           "max_abs_change": float(np.abs(original - values).max())})
    basis = pd.DataFrame(basis_rows)
    basis.to_csv(OUT / "SPLINE_BASIS_COMPLETED.csv", index=False)
    print("DETECTOR ONLY")
    print(metric.to_string(index=False))
    print("\nMETRIC RANK CORRELATION")
    print(pd.DataFrame(corr).to_string(index=False))
    print("\nFIVE SEEDS")
    print(seed_summary.to_string())
    print("\nSEED RANK CORRELATION")
    print(seeds.pivot(index="detector", columns="seed", values="CDU").corr(method="spearman").to_string())
    print("\nCOMPLETED BASIS VARIANTS")
    print(basis.to_string(index=False))


if __name__ == "__main__":
    main()
