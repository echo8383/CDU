from __future__ import annotations
import hashlib, random, sys, time, traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import numpy as np, pandas as pd, torch

ROOT=Path(__file__).resolve().parent; REPO=Path(r'D:\CSIES\AI4Energy\others\TSB-AD')
DATA=ROOT/'Datasets'/'TSB-AD-U'; REF_PATH=ROOT/'uni_vuspr.csv'; FILE_LIST=REPO/'Datasets'/'File_List'/'TSB-AD-U-Eva.csv'
CACHE=ROOT/'layer2_results'/'poly_pinned_scores'; OUT=ROOT/'layer2_results'/'poly_reproducibility_350.csv'; LOG=ROOT/'layer2_results'/'poly_reproducibility_350.log'
SEED=2024; COMMIT='8b363e350ae047a8115a594d1e9da64aae09b852'; HP={'periodicity':1,'power':4}; MODE='official_historical'

def one(fn):
    sys.path.insert(0,str(REPO)); from r0_official_compat import find_length_rank_official_compat
    from TSB_AD.evaluation.basic_metrics import generate_curve as ovus
    from vus_eval.basic_metrics import generate_curve as lvus
    from poly_historical_compat import run_poly_historical
    def seed():
        random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
        if torch.cuda.is_available(): torch.cuda.manual_seed_all(SEED)
        torch.backends.cudnn.benchmark=False; torch.backends.cudnn.deterministic=True
    def dg(a): return hashlib.sha256(np.ascontiguousarray(a,dtype=np.float64).tobytes()).hexdigest()
    t=time.time(); score1=score2=np.array([],dtype=float)
    try:
        df=pd.read_csv(DATA/fn).dropna(); data=df.iloc[:,0:-1].values.astype(float); label=df['Label'].astype(int).to_numpy()
        w=int(find_length_rank_official_compat(data[:,0].reshape(-1,1),rank=1)); seed(); score1=run_poly_historical(data,window=w,power=4); h1=dg(score1)
        seed(); score2=run_poly_historical(data,window=w,power=4); h2=dg(score2)
        lo=len(score1)==len(label) and len(score2)==len(label); f=float(np.isfinite(score1).mean()) if len(score1) else 0.; f2=float(np.isfinite(score2).mean()) if len(score2) else 0.
        ov=float(ovus(label,score1,w,'opt',250)[7]) if lo and f==1. else np.nan; lv=float(lvus(label,score1,w,'opt',250)[7]) if lo and f==1. else np.nan
        hist=float(pd.read_csv(REF_PATH).set_index('file').loc[fn,'POLY']); ld=abs(ov-lv) if np.isfinite(ov) and np.isfinite(lv) else np.nan
        status='PASS' if h1==h2 and lo and f==1. and f2==1. and ld<=1e-12 else 'FAIL'; err=''
        if status=='PASS':
            CACHE.mkdir(parents=True,exist_ok=True); final=CACHE/(fn+'.npy')
            # Each series is assigned once; direct save avoids Windows rename
            # contention with antivirus/indexers on existing cache files.
            with open(final,'wb') as g: np.save(g,np.asarray(score1,dtype=float))
    except Exception as e:
        traceback.print_exc(); h1=dg(score1); h2=dg(score2); lo=False; f=f2=0.; w= np.nan; ov=lv=hist=ld=np.nan; status='FAIL'; err=repr(e); label=np.array([])
    return dict(series_id=fn,length=len(label),selected_window=w,official_historical_vus=hist,pinned_vus=ov,local_vus=lv,local_vus_abs_diff=ld,historical_vus_abs_diff=abs(ov-hist) if np.isfinite(ov) and np.isfinite(hist) else np.nan,score_hash_run1=h1,score_hash_run2=h2,deterministic_hash_match=h1==h2,score_length=len(score1),score_length_match=lo,finite_ratio=f,finite_ratio_run2=f2,status=status,seed=SEED,mode=MODE,repo_commit=COMMIT,hp=repr(HP),error=err,runtime_sec=time.time()-t)

if __name__=='__main__':
    allf=pd.read_csv(FILE_LIST)['file_name'].astype(str).tolist(); existing=set()
    if OUT.exists() and OUT.stat().st_size > 10:
        old=pd.read_csv(OUT); existing=set(old.loc[old.status=='PASS','series_id'])
    pending=[f for f in allf if f not in existing]; old=pd.read_csv(OUT).to_dict('records') if OUT.exists() and OUT.stat().st_size > 10 else []
    print(f'pending={len(pending)} existing_pass={len(existing)}',flush=True)
    with ProcessPoolExecutor(max_workers=4) as ex:
        futs={ex.submit(one,f):f for f in pending}
        for n,fut in enumerate(as_completed(futs),1):
            row=fut.result(); old.append(row); pd.DataFrame(old).to_csv(OUT,index=False)
            with open(LOG,'a',encoding='utf-8') as g: g.write(f"{len(existing)+n}/350 {row['status']} {row['series_id']} len={row['length']} window={row['selected_window']} local_diff={row['local_vus_abs_diff']} sec={row['runtime_sec']:.1f}\n")
            print(f"{len(existing)+n}/350 {row['status']} {row['series_id']} sec={row['runtime_sec']:.1f}",flush=True)
    r=pd.DataFrame(old); print(f"DONE rows={len(r)} pass={(r.status=='PASS').sum()} fail={(r.status!='PASS').sum()} max_local={r.local_vus_abs_diff.max()}")
