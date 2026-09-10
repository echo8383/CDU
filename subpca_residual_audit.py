"""Minimal Sub-PCA R0 residual localization; never runs CDU."""
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, rankdata

from TSB_AD.utils.slidingWindows import find_length_rank
from r0_official_compat import find_length_rank_official_compat
from vus_eval.basic_metrics import generate_curve as local_vus
import importlib.util

_repo_metrics = Path(r"D:\CSIES\AI4Energy\others\TSB-AD\TSB_AD\evaluation\basic_metrics.py")
_spec = importlib.util.spec_from_file_location("tsb_repo_basic_metrics", _repo_metrics)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
repo_vus = _mod.generate_curve

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Datasets" / "TSB-AD-U"
REF = pd.read_csv(ROOT / "uni_vuspr.csv").set_index("file")
SAMPLES = [
    "010_NAB_id_10_WebService_tr_500_1st_271.csv",
    "039_WSD_id_11_WebService_tr_1746_1st_1846.csv",
    "331_UCR_id_29_Facility_tr_50000_1st_837400.csv",
]
OUT = ROOT / "layer2_results" / "subpca_residual_audit.csv"


def stats(x):
    r = rankdata(x, method="average")
    return {
        "score_min": float(np.min(x)),
        "score_max": float(np.max(x)),
        "score_mean": float(np.mean(x)),
        "score_std": float(np.std(x)),
        "score_sha256": hashlib.sha256(np.asarray(x, dtype=np.float64).tobytes()).hexdigest(),
        "rank_sha256": hashlib.sha256(np.asarray(r, dtype=np.float64).tobytes()).hexdigest(),
        "unique_scores": int(np.unique(x).size),
    }


def vus(fn, score, label, window):
    return float(fn(label.astype(int), score.astype(float), int(window), "opt", 250)[7])


rows = []
for f in SAMPLES:
    df = pd.read_csv(DATA / f).dropna()
    x = df.iloc[:, 0].to_numpy(float)
    y = df.Label.to_numpy(int)
    compat_w = find_length_rank_official_compat(x.reshape(-1, 1), 1)
    current_w = find_length_rank(x.reshape(-1, 1), 1)
    raw_path = ROOT / "layer2_results" / "r0_hp_scores" / "Sub-PCA" / (f + ".npy")
    z_path = ROOT / "layer2_results" / "detector_scores" / "Sub-PCA" / (f + ".npy")
    raw = np.load(raw_path).astype(float)
    z = np.load(z_path).astype(float)
    rs = stats(raw)
    zs = stats(z)
    row = {
        "series_id": f,
        "length": len(y),
        "finite_raw": float(np.isfinite(raw).mean()),
        "finite_z": float(np.isfinite(z).mean()),
        "current_window": current_w,
        "compat_window": compat_w,
        "official_vus": float(REF.loc[f, "Sub-PCA"]),
        "raw_repo_vus": vus(repo_vus, raw, y, compat_w),
        "raw_local_vus": vus(local_vus, raw, y, compat_w),
        "z_repo_vus": vus(repo_vus, z, y, compat_w),
        "z_local_vus": vus(local_vus, z, y, compat_w),
        "raw_vus_window_current": vus(repo_vus, raw, y, current_w),
        "raw_z_spearman": float(spearmanr(raw, z).statistic),
        "raw_rank_agreement": float(np.mean(rankdata(raw) == rankdata(z))),
        "raw_z_max_abs": float(np.max(np.abs(raw - z))),
        "raw_z_norm_ratio_std": float(np.std(z) / np.std(raw)),
        **{f"raw_{k}": v for k, v in rs.items()},
        **{f"z_{k}": v for k, v in zs.items()},
    }
    rows.append(row)
    print(f, row["current_window"], row["compat_window"], row["official_vus"], row["raw_repo_vus"], row["raw_local_vus"], row["z_repo_vus"])

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)
print(out[["series_id", "compat_window", "official_vus", "raw_repo_vus", "raw_local_vus", "z_repo_vus", "raw_z_spearman"]].to_string(index=False))
print("max raw repo diff", float(np.max(np.abs(out.raw_repo_vus - out.official_vus))) )
print("max raw local diff", float(np.max(np.abs(out.raw_local_vus - out.official_vus))) )
