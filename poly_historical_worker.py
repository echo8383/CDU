"""One-file worker for the explicit historical POLY R0 audit."""
from __future__ import annotations
import argparse, hashlib, random, sys, time, traceback, json
from pathlib import Path
import numpy as np, pandas as pd, torch
ROOT=Path(__file__).resolve().parent; REPO=Path(r'D:\CSIES\AI4Energy\others\TSB-AD'); sys.path.insert(0,str(REPO))
from r0_official_compat import find_length_rank_official_compat
from TSB_AD.evaluation.basic_metrics import generate_curve
from poly_historical_compat import run_poly_historical, HISTORICAL_HP, MODE
SEED=2024; COMMIT='8b363e350ae047a8115a594d1e9da64aae09b852'
def sha(a): return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def main(index):
 files=pd.read_csv(REPO/'Datasets'/'File_List'/'TSB-AD-U-Eva.csv')['file_name'].astype(str).tolist(); f=files[index-1]; t=time.time()
 try:
  random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED); torch.cuda.manual_seed(SEED); torch.cuda.manual_seed_all(SEED); torch.backends.cudnn.benchmark=False; torch.backends.cudnn.deterministic=True
  df=pd.read_csv(ROOT/'Datasets'/'TSB-AD-U'/f).dropna(); x=df.iloc[:,0:-1].values.astype(float); y=df.Label.astype(int).to_numpy(); w=int(find_length_rank_official_compat(x[:,0].reshape(-1,1),1))
  s=np.asarray(run_poly_historical(x,window=w,power=HISTORICAL_HP['power']),float).ravel(); finite=float(np.isfinite(s).mean()); valid=len(s)==len(y) and finite==1.0; v=float(generate_curve(y,s,w,'opt',250)[7]) if valid else float('nan'); off=float(pd.read_csv(ROOT/'uni_vuspr.csv').set_index('file').loc[f,'POLY']); diff=abs(v-off) if valid else float('nan'); status='PASS' if valid and diff<1e-6 else 'FAIL'; row={'mode':MODE,'detector':'POLY','series_id':f,'index':index,'length':len(y),'selected_window':w,'official_VUS':off,'reproduced_VUS':v,'abs_diff':diff,'finite_ratio':finite,'score_length':len(s),'score_length_match':len(s)==len(y),'score_hash':sha(s),'status':status,'runtime_sec':time.time()-t,'seed':SEED,'repo_commit':COMMIT,'hp':repr(HISTORICAL_HP),'error':''}; print(row,flush=True); return row
 except Exception as e:
  row={'mode':MODE,'detector':'POLY','series_id':f,'index':index,'status':'FAIL','error':repr(e)}; traceback.print_exc(); print(row,flush=True); return row
if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('--index',type=int,required=True); a=ap.parse_args(); row=main(a.index); (ROOT/'layer2_results'/'poly_historical_workers').mkdir(parents=True,exist_ok=True); (ROOT/'layer2_results'/'poly_historical_workers'/f'{a.index:04d}.json').write_text(json.dumps(row,default=str),encoding='utf-8')
