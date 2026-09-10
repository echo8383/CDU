"""R0-Reproducibility for a pinned, historical-compatible POLY environment.

This gate deliberately does *not* compare pinned VUS to the historical
leaderboard as a pass criterion.  It checks deterministic point-wise scores,
alignment, finite values, and deterministic local VUS computation.
"""
from __future__ import annotations
import hashlib, random, sys, time, traceback
from pathlib import Path
import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parent
REPO = Path(r"D:\CSIES\AI4Energy\others\TSB-AD")
DATA = ROOT / "Datasets" / "TSB-AD-U"
REF_PATH = ROOT / "uni_vuspr.csv"
FILE_LIST = REPO / "Datasets" / "File_List" / "TSB-AD-U-Eva.csv"
CACHE = ROOT / "layer2_results" / "poly_pinned_scores"
OUT = ROOT / "layer2_results" / "poly_reproducibility_350.csv"
REPORT = ROOT / "R0_REPRODUCIBLE_POLY.md"
SEED = 2024
COMMIT = "8b363e350ae047a8115a594d1e9da64aae09b852"
HP = {"periodicity": 1, "power": 4}
MODE = "official_historical"

sys.path.insert(0, str(REPO))
from r0_official_compat import find_length_rank_official_compat
from TSB_AD.evaluation.basic_metrics import generate_curve as official_vus
from poly_historical_compat import run_poly_historical
from vus_eval.basic_metrics import generate_curve as local_vus

def seed_all(seed: int = SEED):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True

def digest(a):
    return hashlib.sha256(np.ascontiguousarray(a, dtype=np.float64).tobytes()).hexdigest()

def main(limit: int | None = None, resume: bool = False):
    CACHE.mkdir(parents=True, exist_ok=True)
    ref = pd.read_csv(REF_PATH).set_index("file")
    files = pd.read_csv(FILE_LIST)["file_name"].astype(str).tolist()
    if limit is not None: files = files[:limit]
    rows, started = [], time.time()
    if resume and OUT.exists():
        prev = pd.read_csv(OUT)
        rows = prev[prev.status == "PASS"].to_dict("records")
        done = {r["series_id"] for r in rows}
        files = [f for f in files if f not in done]
    for ix, fn in enumerate(files, 1):
        t0 = time.time(); score1 = score2 = np.array([], dtype=float)
        try:
            df = pd.read_csv(DATA / fn).dropna()
            data = df.iloc[:, 0:-1].values.astype(float)
            label = df["Label"].astype(int).to_numpy()
            window = int(find_length_rank_official_compat(data[:, 0].reshape(-1, 1), rank=1))
            seed_all(); score1 = run_poly_historical(data, window=window, power=HP["power"])
            hash1 = digest(score1)
            seed_all(); score2 = run_poly_historical(data, window=window, power=HP["power"])
            hash2 = digest(score2)
            length_ok = len(score1) == len(label) and len(score2) == len(label)
            finite = float(np.isfinite(score1).mean()) if len(score1) else 0.0
            finite2 = float(np.isfinite(score2).mean()) if len(score2) else 0.0
            # Use the cached first run as the pinned score.
            pinned = np.asarray(score1, dtype=float).ravel()
            ov = float(official_vus(label, pinned, window, "opt", 250)[7]) if length_ok and finite == 1.0 else np.nan
            lv = float(local_vus(label, pinned, window, "opt", 250)[7]) if length_ok and finite == 1.0 else np.nan
            local_diff = abs(ov - lv) if np.isfinite(ov) and np.isfinite(lv) else np.nan
            hist = float(ref.loc[fn, "POLY"])
            hist_diff = abs(ov - hist) if np.isfinite(ov) else np.nan
            deterministic = hash1 == hash2
            status = "PASS" if deterministic and length_ok and finite == 1.0 and finite2 == 1.0 and local_diff <= 1e-12 else "FAIL"
            if status == "PASS":
                tmp = CACHE / (fn + ".npy.tmp"); final = CACHE / (fn + ".npy")
                with open(tmp, "wb") as f: np.save(f, pinned)
                tmp.replace(final)
            err = ""
        except Exception as e:
            traceback.print_exc(); hist = float(ref.loc[fn, "POLY"]) if fn in ref.index else np.nan
            hash1 = digest(score1); hash2 = digest(score2); ov = lv = local_diff = hist_diff = np.nan
            window = np.nan; length_ok = False; finite = finite2 = 0.0; deterministic = False
            status = "FAIL"; err = repr(e)
        row = dict(index=ix, series_id=fn, length=len(label) if 'label' in locals() else -1,
                   selected_window=window, official_historical_vus=hist,
                   pinned_vus=ov, local_vus=lv, local_vus_abs_diff=local_diff,
                   historical_vus_abs_diff=hist_diff, score_hash_run1=hash1,
                   score_hash_run2=hash2, deterministic_hash_match=deterministic,
                   score_length=len(score1), score_length_match=length_ok,
                   finite_ratio=finite, finite_ratio_run2=finite2, status=status,
                   seed=SEED, mode=MODE, repo_commit=COMMIT, hp=repr(HP), error=err,
                   runtime_sec=time.time()-t0)
        rows.append(row); pd.DataFrame(rows).to_csv(OUT, index=False)
        print(f"{ix}/{len(files)} {status} {fn} len={row['length']} window={window} local_diff={local_diff} hist_diff={hist_diff} sec={row['runtime_sec']:.1f}", flush=True)
        if status == "FAIL":
            print("R0-REPRODUCIBILITY STOP: first failure recorded", flush=True)
            break
    r = pd.DataFrame(rows)
    passed = int((r.status == "PASS").sum()) if len(r) else 0
    all_pass = len(r) == len(files) and passed == len(files)
    max_local = float(r.local_vus_abs_diff.max()) if len(r) else np.nan
    report = f"""# R0-Reproducible POLY\n\n- Mode: `{MODE}`\n- Repository commit: `{COMMIT}`\n- Seed: `{SEED}`\n- Hyperparameters: `{HP}`\n- Window: historical-compatible `find_length_rank`\n- Input: `pd.read_csv(...).dropna(); df.iloc[:,0:-1].astype(float)`\n- Dependencies: numpy {np.__version__}, pandas {pd.__version__}, torch {torch.__version__}\n\n## Result\n\n- Requested series: {len(files)}\n- Completed: {len(r)}\n- PASS: {passed}\n- Gate: **{'PASS' if all_pass else 'FAIL'}**\n- Max local VUS implementation difference: {max_local}\n\nHistorical leaderboard VUS and `historical_vus_abs_diff` are retained as provenance divergence only; they are not a gate criterion.\n"""
    REPORT.write_text(report, encoding="utf-8")
    print(report)
    return 0 if all_pass else 2

if __name__ == "__main__":
    lim = None
    if "--limit" in sys.argv:
        lim = int(sys.argv[sys.argv.index("--limit") + 1])
    raise SystemExit(main(lim, "--resume" in sys.argv))
