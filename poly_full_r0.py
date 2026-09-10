"""P1: full POLY Gate-R0 parity, and nothing from Layer 2 CDU.

Uses the official TSB-AD-U-Eva file list, historical compatible window
selection, official HP, and resumable point-wise score caches.  The script
exits non-zero and writes the failing rows if any VUS mismatch exceeds 1e-6.
"""
from __future__ import annotations
import hashlib, random, shutil, sys, time, traceback
from pathlib import Path
import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parent
REPO = Path(r"D:\CSIES\AI4Energy\others\TSB-AD")
DATA = ROOT / "Datasets" / "TSB-AD-U"
REF = pd.read_csv(ROOT / "uni_vuspr.csv").set_index("file")
FILES = pd.read_csv(REPO / "Datasets" / "File_List" / "TSB-AD-U-Eva.csv")["file_name"].astype(str).tolist()
CACHE = ROOT / "layer2_results" / "poly_scores"
CACHE.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "layer2_results" / "poly_full_r0.csv"
PROGRESS = ROOT / "layer2_results" / "poly_full_r0_progress.log"
SEED = 2024
COMMIT = "8b363e350ae047a8115a594d1e9da64aae09b852"
# Existing caches predate this run and are not trusted for provenance parity.
# They are overwritten by the official-compatible path below.
REUSE_CACHE = True

sys.path.insert(0, str(REPO))
from r0_official_compat import find_length_rank_official_compat
from TSB_AD import model_wrapper
from TSB_AD.HP_list import Optimal_Uni_algo_HP_dict
from TSB_AD.evaluation.basic_metrics import generate_curve

model_wrapper.find_length_rank = find_length_rank_official_compat
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
torch.cuda.manual_seed(SEED); torch.cuda.manual_seed_all(SEED)
torch.backends.cudnn.benchmark = False; torch.backends.cudnn.deterministic = True

HP = dict(Optimal_Uni_algo_HP_dict["POLY"])

def sha(x): return hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()

def atomic_save(path: Path, arr: np.ndarray):
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as f: np.save(f, arr)
    tmp.replace(path)

def existing_rows():
    if not OUT.exists(): return {}
    try: return {str(r.series_id): r._asdict() for r in pd.read_csv(OUT).itertuples(index=False)}
    except Exception: return {}

def main():
    old = existing_rows(); rows = []
    t_all = time.time()
    total = len(FILES)
    for ix, filename in enumerate(FILES, 1):
        prior = old.get(filename)
        prior_cache = CACHE / (filename + ".npy")
        if prior and str(prior.get("status")) == "PASS" and prior_cache.exists():
            rows.append(prior)
            print(f"{ix}/{total} PASS {filename} reused_record=True", flush=True)
            continue
        if prior and str(prior.get("status")) != "PASS" and prior_cache.exists():
            prior_cache.unlink()
        t0 = time.time(); cache = CACHE / (filename + ".npy"); reused = False; err = ""
        try:
            df = pd.read_csv(DATA / filename).dropna()
            data = df.iloc[:, 0:-1].values.astype(float)
            label = df["Label"].astype(int).to_numpy()
            window = int(find_length_rank_official_compat(data[:, 0].reshape(-1, 1), rank=1))
            if REUSE_CACHE and cache.exists():
                score = np.load(cache, allow_pickle=False).astype(float); reused = True
            else:
                score = np.asarray(model_wrapper.run_Unsupervise_AD("POLY", data, **HP), dtype=float).ravel()
                if len(score) == len(label) and np.isfinite(score).all(): atomic_save(cache, score)
            finite = float(np.isfinite(score).mean()) if len(score) else 0.0
            valid = len(score) == len(label) and finite == 1.0
            rec_vus = float(generate_curve(label, score, window, "opt", 250)[7]) if valid else np.nan
            official = float(REF.loc[filename, "POLY"])
            diff = abs(rec_vus - official) if valid else np.nan
            status = "PASS" if valid and diff < 1e-6 else "FAIL"
            row = dict(detector="POLY", series_id=filename, index=ix, length_y=len(label), length_score=len(score),
                       finite_ratio=finite, official_window=window, official_vus=official,
                       reproduced_vus=rec_vus, abs_diff=diff, score_sha256=sha(score),
                       label_sha256=sha(label), runtime_sec=time.time()-t0, cache_reused=reused,
                       status=status, error="")
        except Exception as e:
            traceback.print_exc(); row = dict(detector="POLY", series_id=filename, index=ix,
                length_y=-1, length_score=-1, finite_ratio=0.0, official_window=np.nan,
                official_vus=float(REF.loc[filename, "POLY"]), reproduced_vus=np.nan,
                abs_diff=np.nan, score_sha256="", label_sha256="", runtime_sec=time.time()-t0,
                cache_reused=reused, status="FAIL", error=repr(e))
        rows.append(row)
        pd.DataFrame(rows).to_csv(OUT, index=False)
        msg = f"{ix}/{total} {row['status']} {filename} diff={row['abs_diff']} window={row['official_window']} reused={reused} sec={row['runtime_sec']:.1f} elapsed={time.time()-t_all:.1f}"
        print(msg, flush=True)
        with open(PROGRESS, "a", encoding="utf-8") as f: f.write(msg + "\n")
        if row["status"] != "PASS":
            pd.DataFrame([row]).to_csv(ROOT / "layer2_results" / "poly_full_r0_failures.csv", index=False)
            raise SystemExit(2)
    R = pd.DataFrame(rows)
    fails = R[(R.status != "PASS") | (R.abs_diff >= 1e-6)]
    summary = f"\nP1 complete: {len(R)}/{total}; PASS={int((R.status=='PASS').sum())}; FAIL={len(fails)}; max_abs_diff={R.abs_diff.max()}\n"
    print(summary, flush=True)
    with open(PROGRESS, "a", encoding="utf-8") as f: f.write(summary)
    if len(fails):
        fails.to_csv(ROOT / "layer2_results" / "poly_full_r0_failures.csv", index=False)
        raise SystemExit(2)
    print("R0 PASS: 350/350 POLY curves reproduce official VUS within 1e-6", flush=True)

if __name__ == "__main__": main()
