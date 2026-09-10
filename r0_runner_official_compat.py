"""Gate R0 runner using the historical official window semantics.

This is an R0-only reproduction script. It does not import or run CDU.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parent
TSB_REPO = Path(r"D:\CSIES\AI4Energy\others\TSB-AD")
sys.path.insert(0, str(TSB_REPO))

from r0_official_compat import find_length_rank_official_compat
from TSB_AD import model_wrapper
from TSB_AD.HP_list import Optimal_Uni_algo_HP_dict
from TSB_AD.evaluation.basic_metrics import generate_curve


# Patch the helper imported into wrapper functions. No detector behavior is
# changed except restoring the historical window fallback.
model_wrapper.find_length_rank = find_length_rank_official_compat

SEED = 2024
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True

DATA = ROOT / "Datasets" / "TSB-AD-U"
REF = pd.read_csv(ROOT / "uni_vuspr.csv").set_index("file")
SAMPLES = pd.read_csv(ROOT / "layer2_results" / "score_reproduction.csv")
OUT = ROOT / "layer2_results" / "r0_official_compat_parity.csv"

NAME = {"Sub-PCA": "Sub_PCA", "POLY": "POLY"}


def main() -> None:
    rows = []
    for _, rec in SAMPLES.iterrows():
        detector = rec.detector
        filename = rec.series_id
        df = pd.read_csv(DATA / filename).dropna()
        data = df.iloc[:, 0:-1].values.astype(float)
        label = df.Label.astype(int).to_numpy()
        window = find_length_rank_official_compat(data[:, 0].reshape(-1, 1), 1)
        hp = Optimal_Uni_algo_HP_dict[NAME[detector]]
        if NAME[detector] in model_wrapper.Unsupervise_AD_Pool:
            score = np.asarray(
                model_wrapper.run_Unsupervise_AD(NAME[detector], data, **hp),
                dtype=float,
            ).ravel()
        else:
            raise RuntimeError(f"unexpected pool for {detector}")
        vus = float(generate_curve(label, score, window, "opt", 250)[7])
        official = float(REF.loc[filename, detector])
        row = {
            "detector": detector,
            "series_id": filename,
            "length_y": len(label),
            "length_score": len(score),
            "finite_ratio": float(np.isfinite(score).mean()),
            "official_window_compat": int(window),
            "official_vus": official,
            "compat_vus": vus,
            "abs_diff": abs(vus - official),
            "hp": repr(hp),
            "seed": SEED,
            "repo_commit": "8b363e350ae047a8115a594d1e9da64aae09b852",
        }
        rows.append(row)
        print(row, flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    print(out[["detector", "series_id", "official_window_compat", "abs_diff"]].to_string(index=False))
    print("max_abs_diff", float(out.abs_diff.max()))


if __name__ == "__main__":
    main()
