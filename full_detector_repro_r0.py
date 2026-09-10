"""Full 350-series pinned R0-Reproducibility for one screened detector."""
from __future__ import annotations
import argparse, hashlib, random, sys, time, traceback
from pathlib import Path
import numpy as np, pandas as pd, torch

ROOT=Path(__file__).resolve().parent; REPO=Path(r'D:\CSIES\AI4Energy\others\TSB-AD'); DATA=ROOT/'Datasets'/'TSB-AD-U'; L2=ROOT/'layer2_results'
sys.path.insert(0,str(REPO)); from TSB_AD.HP_list import Optimal_Uni_algo_HP_dict
from TSB_AD import model_wrapper as mw
from TSB_AD.evaluation.basic_metrics import generate_curve as official_vus
from vus_eval.basic_metrics import generate_curve as local_vus
from r0_official_compat import patch_model_wrapper,find_length_rank_official_compat
patch_model_wrapper(mw)
SEED=2024; COMMIT='8b363e350ae047a8115a594d1e9da64aae09b852'; TABLE={'Sub_IForest':'Sub-IForest','Sub_LOF':'Sub-LOF','Sub_HBOS':'Sub-HBOS','Sub_KNN':'Sub-KNN'}
def seed():
 random.seed(SEED);np.random.seed(SEED);torch.manual_seed(SEED);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
 if torch.cuda.is_available():torch.cuda.manual_seed_all(SEED)
def digest(a):return hashlib.sha256(np.ascontiguousarray(a,dtype=np.float64).tobytes()).hexdigest()
def main(det):
 hp=Optimal_Uni_algo_HP_dict[det]; ref=pd.read_csv(ROOT/'uni_vuspr.csv').set_index('file'); files=ref.index.tolist(); out=L2/f'{det}_reproducibility_350.csv'; cache=L2/'detector_pinned_scores'/det; cache.mkdir(parents=True,exist_ok=True); rows=[]; done=set()
 if out.exists() and out.stat().st_size>10:
  old=pd.read_csv(out); rows=old[old.status=='PASS'].to_dict('records'); done={x['series_id'] for x in rows}
 for ix,f in enumerate(files,1):
  if f in done: continue
  t=time.time();s1=s2=np.array([],float)
  try:
   df=pd.read_csv(DATA/f).dropna();x=df.iloc[:,:-1].values.astype(float);y=df.Label.astype(int).to_numpy();w=int(find_length_rank_official_compat(x[:,0].reshape(-1,1),1))
   seed();s1=np.asarray(mw.run_Unsupervise_AD(det,x,**hp),float).ravel();h1=digest(s1);seed();s2=np.asarray(mw.run_Unsupervise_AD(det,x,**hp),float).ravel();h2=digest(s2)
   length=len(s1)==len(y) and len(s2)==len(y);finite=float(np.isfinite(s1).mean()) if len(s1) else 0.;finite2=float(np.isfinite(s2).mean()) if len(s2) else 0.
   ov=float(official_vus(y,s1,w,'opt',250)[7]) if length and finite==1 else np.nan;lv=float(local_vus(y,s1,w,'opt',250)[7]) if length and finite==1 else np.nan; ld=abs(ov-lv) if np.isfinite(ov) and np.isfinite(lv) else np.nan
   status='PASS' if h1==h2 and length and finite==1 and finite2==1 and ld<=1e-12 else 'FAIL';err=''
   if status=='PASS':
    with open(cache/(f+'.npy'),'wb') as z:np.save(z,s1)
   hist=float(ref.loc[f,TABLE.get(det,det)])
  except Exception as e:
   h1=digest(s1);h2=digest(s2);length=False;finite=finite2=0.;ov=lv=ld=hist=np.nan;w=np.nan;status='FAIL';err=repr(e)
  rows.append({'index':ix,'detector':det,'series_id':f,'hp':repr(hp),'seed':SEED,'repo_commit':COMMIT,'selected_window':w,'score_hash_run1':h1,'score_hash_run2':h2,'hash_match':h1==h2,'score_length':len(s1),'score_length_match':length,'finite_ratio':finite,'finite_ratio_run2':finite2,'pinned_vus':ov,'local_vus':lv,'local_vus_abs_diff':ld,'historical_vus':hist,'historical_vus_abs_diff':abs(ov-hist) if np.isfinite(ov) and np.isfinite(hist) else np.nan,'status':status,'runtime_sec':time.time()-t,'error':err})
  pd.DataFrame(rows).to_csv(out,index=False);print(f'{det} {ix}/350 {status} {f} sec={rows[-1]["runtime_sec"]:.1f}',flush=True)
  if status!='PASS':break
 r=pd.DataFrame(rows); print(f'DONE {det} rows={len(r)} pass={(r.status=="PASS").sum()} fail={(r.status!="PASS").sum()}',flush=True)
 return 0 if len(r)==350 and (r.status=='PASS').all() else 2
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('detector');a=p.parse_args();raise SystemExit(main(a.detector))
