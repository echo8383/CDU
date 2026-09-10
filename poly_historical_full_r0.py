"""Full 350-series strict R0 validation for explicit historical POLY mode.

Starts at series 1, uses a separate cache, and stops immediately at the first
failure.  No CDU code is imported or run here.
"""
from __future__ import annotations
import hashlib, random, sys, time, traceback
from pathlib import Path
import numpy as np, pandas as pd, torch

ROOT = Path(__file__).resolve().parent
REPO = Path(r"D:\CSIES\AI4Energy\others\TSB-AD")
DATA = ROOT / "Datasets" / "TSB-AD-U"
REF = pd.read_csv(ROOT / "uni_vuspr.csv").set_index("file")
FILES = pd.read_csv(REPO / "Datasets" / "File_List" / "TSB-AD-U-Eva.csv")["file_name"].astype(str).tolist()
CACHE = ROOT / "layer2_results" / "poly_historical_scores"
OUT = ROOT / "layer2_results" / "poly_historical_full_r0.csv"
FAIL = ROOT / "layer2_results" / "poly_historical_r0_failures.csv"
LOG = ROOT / "layer2_results" / "poly_historical_full_r0.log"
SEED = 2024
COMMIT = "8b363e350ae047a8115a594d1e9da64aae09b852"
CACHE.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(REPO))
from r0_official_compat import find_length_rank_official_compat
from TSB_AD.evaluation.basic_metrics import generate_curve
from poly_historical_compat import run_poly_historical, HISTORICAL_HP, MODE

random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
torch.cuda.manual_seed(SEED); torch.cuda.manual_seed_all(SEED)
torch.backends.cudnn.benchmark = False; torch.backends.cudnn.deterministic = True

def sha(a): return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def atomic_save(path, a):
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as f: np.save(f, a)
    tmp.replace(path)

def main():
    # From-scratch audit: remove only this mode's prior output/cache, never
    # touch modern or prior compatibility caches.
    for p in (OUT, FAIL, LOG):
        if p.exists(): p.unlink()
    for p in CACHE.glob("*.npy"):
        p.unlink()
    rows=[]; t_all=time.time(); total=len(FILES)
    for ix, filename in enumerate(FILES, 1):
        t0=time.time(); status="FAIL"; err=""; score=np.array([], dtype=float)
        try:
            df=pd.read_csv(DATA / filename).dropna()
            data=df.iloc[:,0:-1].values.astype(float)
            label=df["Label"].astype(int).to_numpy()
            window=int(find_length_rank_official_compat(data[:,0].reshape(-1,1), rank=1))
            score=run_poly_historical(data, window=window, power=HISTORICAL_HP["power"])
            finite=float(np.isfinite(score).mean()) if len(score) else 0.0
            length_ok=len(score)==len(label)
            valid=length_ok and finite==1.0
            reproduced=float(generate_curve(label, score, window, "opt", 250)[7]) if valid else np.nan
            official=float(REF.loc[filename,"POLY"])
            diff=abs(reproduced-official) if valid else np.nan
            status="PASS" if valid and diff < 1e-6 else "FAIL"
            if length_ok and finite==1.0:
                atomic_save(CACHE/(filename+".npy"), score)
            row=dict(mode=MODE, detector="POLY", series_id=filename, index=ix,
                     length=len(label), selected_window=window, official_VUS=official,
                     reproduced_VUS=reproduced, abs_diff=diff, finite_ratio=finite,
                     score_length=len(score), score_length_match=length_ok,
                     score_hash=sha(score), status=status, runtime_sec=time.time()-t0,
                     seed=SEED, repo_commit=COMMIT, hp=repr(HISTORICAL_HP), error="")
        except Exception as e:
            err=repr(e); traceback.print_exc()
            row=dict(mode=MODE, detector="POLY", series_id=filename, index=ix,
                     length=len(label) if 'label' in locals() else -1, selected_window=np.nan,
                     official_VUS=float(REF.loc[filename,"POLY"]), reproduced_VUS=np.nan,
                     abs_diff=np.nan, finite_ratio=0.0, score_length=len(score),
                     score_length_match=False, score_hash=sha(score), status="FAIL",
                     runtime_sec=time.time()-t0, seed=SEED, repo_commit=COMMIT,
                     hp=repr(HISTORICAL_HP), error=err)
        rows.append(row); pd.DataFrame(rows).to_csv(OUT,index=False)
        msg=f"{ix}/{total} {row['status']} {filename} diff={row['abs_diff']} window={row['selected_window']} sec={row['runtime_sec']:.2f} elapsed={time.time()-t_all:.1f}"
        print(msg, flush=True)
        with open(LOG,"a",encoding="utf-8") as f: f.write(msg+"\n")
        if status != "PASS":
            pd.DataFrame([row]).to_csv(FAIL,index=False)
            raise SystemExit(2)
    R=pd.DataFrame(rows); dif=R.abs_diff.astype(float)
    summary=f"PASS {len(R)}/{total}; max={dif.max()}; mean={dif.mean()}; median={dif.median()}\n"
    with open(LOG,"a",encoding="utf-8") as f: f.write(summary)
    print(summary,flush=True)

if __name__=='__main__': main()
