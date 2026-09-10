"""Pinned R0-reproducibility screening only; does not calculate CDU."""
from __future__ import annotations
import hashlib, random, sys, time, traceback
from pathlib import Path
import numpy as np, pandas as pd, torch

ROOT=Path(__file__).resolve().parent; REPO=Path(r'D:\CSIES\AI4Energy\others\TSB-AD'); DATA=ROOT/'Datasets'/'TSB-AD-U'; OUT=ROOT/'data'; CACHE=ROOT/'layer2_results'/'detector_screen_scores'
sys.path.insert(0,str(REPO)); from TSB_AD.HP_list import Optimal_Uni_algo_HP_dict
from TSB_AD import model_wrapper as mw
from TSB_AD.evaluation.basic_metrics import generate_curve as official_vus
from vus_eval.basic_metrics import generate_curve as local_vus
from r0_official_compat import find_length_rank_official_compat, patch_model_wrapper
patch_model_wrapper(mw)
SEED=2024; COMMIT='8b363e350ae047a8115a594d1e9da64aae09b852'
CANDIDATES=['Sub_IForest','IForest','Sub_LOF','LOF','MatrixProfile','Sub_HBOS','Sub_KNN','KShapeAD','Series2Graph']
TABLE={'Sub_IForest':'Sub-IForest','Sub_LOF':'Sub-LOF','Sub_HBOS':'Sub-HBOS','Sub_KNN':'Sub-KNN'}
SAMPLES=['001_NAB_id_1_Facility_tr_1007_1st_2014.csv','039_WSD_id_11_WebService_tr_1746_1st_1846.csv','141_MSL_id_2_Sensor_tr_500_1st_550.csv','179_SMD_id_2_Facility_tr_5925_1st_17580.csv']
def seed():
    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(SEED)
    torch.backends.cudnn.benchmark=False; torch.backends.cudnn.deterministic=True
def digest(a): return hashlib.sha256(np.ascontiguousarray(a,dtype=np.float64).tobytes()).hexdigest()
def main():
    # Leave a row even when a dependency/model fails: unavailable is never a pass.
    ref=pd.read_csv(ROOT/'uni_vuspr.csv').set_index('file'); rows=[]; OUT.mkdir(exist_ok=True); CACHE.mkdir(exist_ok=True)
    for det in CANDIDATES:
        hp=Optimal_Uni_algo_HP_dict[det]; col=TABLE.get(det,det)
        for f in SAMPLES:
            t=time.time(); s1=s2=np.array([],float)
            try:
                df=pd.read_csv(DATA/f).dropna(); x=df.iloc[:,:-1].values.astype(float); y=df.Label.astype(int).to_numpy(); w=int(find_length_rank_official_compat(x[:,0].reshape(-1,1),1))
                seed(); a=mw.run_Unsupervise_AD(det,x,**hp); s1=np.asarray(a,float).ravel(); h1=digest(s1)
                seed(); a=mw.run_Unsupervise_AD(det,x,**hp); s2=np.asarray(a,float).ravel(); h2=digest(s2)
                length=len(s1)==len(y) and len(s2)==len(y); finite=float(np.isfinite(s1).mean()) if len(s1) else 0.; finite2=float(np.isfinite(s2).mean()) if len(s2) else 0.
                ov=float(official_vus(y,s1,w,'opt',250)[7]) if length and finite==1 else np.nan; lv=float(local_vus(y,s1,w,'opt',250)[7]) if length and finite==1 else np.nan
                diff=abs(ov-lv) if np.isfinite(ov) and np.isfinite(lv) else np.nan; status='PASS' if h1==h2 and length and finite==1 and finite2==1 and diff<=1e-12 else 'FAIL'; err=''
                if status=='PASS':
                    d=CACHE/det; d.mkdir(exist_ok=True)
                    with open(d/(f+'.npy'),'wb') as z: np.save(z,s1)
                hist=float(ref.loc[f,col]) if col in ref.columns else np.nan
            except Exception as e:
                h1=digest(s1); h2=digest(s2); length=False; finite=finite2=0.; ov=lv=diff=hist=np.nan; w=np.nan; status='FAIL'; err=repr(e)
            row={'detector':det,'table_detector':col,'series_id':f,'hp':repr(hp),'selected_window':w,'seed':SEED,'repo_commit':COMMIT,'score_hash_run1':h1,'score_hash_run2':h2,'hash_match':h1==h2,'score_length':len(s1),'score_length_match':length,'finite_ratio':finite,'finite_ratio_run2':finite2,'pinned_vus':ov,'local_vus':lv,'local_vus_abs_diff':diff,'historical_vus':hist,'historical_vus_abs_diff':abs(ov-hist) if np.isfinite(ov) and np.isfinite(hist) else np.nan,'status':status,'runtime_sec':time.time()-t,'error':err}
            rows.append(row); pd.DataFrame(rows).to_csv(OUT/'detector_reproducibility_screen.csv',index=False)
            print(f'{det} {f} {status} sec={row["runtime_sec"]:.1f} err={err[:100]}',flush=True)
    r=pd.DataFrame(rows); summary=r.groupby('detector').agg(screened=('series_id','count'),passed=('status',lambda x:(x=='PASS').sum()),max_local_diff=('local_vus_abs_diff','max'),mean_runtime_sec=('runtime_sec','mean')).reset_index(); summary['status']=np.where(summary.passed==len(SAMPLES),'PASS','FAIL'); summary.to_csv(OUT/'detector_reproducibility_screen_summary.csv',index=False); print(summary.to_string(index=False))
if __name__=='__main__': main()
