"""Aggregate completed leave-one-family-out results and rank stability."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from evaluate_cdu_protocol_v1 import DETECTORS
from run_basis_sensitivity import FAMILIES, ROOT
from run_protocol_v1_controls import atomic_csv


def main():
    root = ROOT / "protocol_basis_results/cap2048"
    primary = (pd.read_csv(ROOT / "paper/evidence/fast_main/MAIN_RESULTS.csv")
               .rename(columns={"Detector": "detector"}).set_index("detector"))
    rows, ranks = [], []
    for family in FAMILIES:
        values = []
        for detector in DETECTORS:
            path = root / f"drop_{family}" / detector / "SUMMARY.csv"
            if not path.exists():
                continue
            item = pd.read_csv(path).iloc[0].to_dict()
            item["dropped_family"] = family
            rows.append(item)
            values.append(item)
        if len(values) == len(DETECTORS):
            frame = pd.DataFrame(values).set_index("detector").loc[list(DETECTORS)]
            aligned = primary.loc[list(DETECTORS)]
            rho = spearmanr(aligned.CDU, frame.CDU).statistic
            ranks.append({"dropped_family": family, "rho_vs_full_basis": rho,
                          "max_abs_cdu_change": float(np.max(np.abs(frame.CDU-aligned.CDU))),
                          "n_detectors": len(frame)})
    output = ROOT / "paper/evidence/basis_sensitivity/cap2048"
    atomic_csv(pd.DataFrame(rows), output / "SUMMARY.csv")
    atomic_csv(pd.DataFrame(ranks), output / "RANK_STABILITY.csv")
    print(pd.DataFrame(ranks).to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
