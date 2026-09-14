"""Recompute Raw VUS from existing detector score caches only.

No detector is imported or executed.  Results are checkpointed per detector.
"""
from pathlib import Path
import argparse, hashlib, time, sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
L2=ROOT/'layer2_results'; DATA=ROOT/'Datasets'/'TSB-AD-U'
sys.path.insert(0,str(ROOT)); sys.path.insert(0,r'D:\CSIES\AI4Energy\others\TSB-AD')
from vus_eval.basic_metrics import generate_curve
from cdu.tsb_ad_compat import find_length_rank_official_compat

REF=pd.read_csv(ROOT/'uni_vuspr.csv'); FILES=REF.file.astype(str).tolist()
CACHE={d:(L2/'poly_pinned_scores' if d=='POLY' else L2/'detector_scores'/d) for d in ['M2N2','TranAD','TimesNet','FITS']}

def labels_and_window(f):
 d=pd.read_csv(DATA/f).dropna(); y=d['Label'].to_numpy(np.int8)
 x=d.iloc[:,:-1].to_numpy(float)
 w=int(find_length_rank_official_compat(x[:,0].reshape(-1,1),rank=1))
 return y,w

def digest(s): return hashlib.sha256(np.ascontiguousarray(s,dtype=np.float64).tobytes()).hexdigest()

def one(det,f):
 y,w=labels_and_window(f); s=np.load(CACHE[det]/(f+'.npy'),allow_pickle=False).reshape(-1)
 if len(s)!=len(y): raise ValueError(f'length mismatch {len(s)} vs {len(y)}')
 if not np.isfinite(s).all(): raise ValueError('non-finite score')
 v=0.0 if np.ptp(s)==0 else float(generate_curve(y,s,w,'opt',250)[7])
 return {'detector':det,'series_id':f,'length':len(y),'window_from_raw_data':w,'VUS_PR':v,'finite_ratio':1.0,'score_hash':digest(s),'status':'PASS'}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--detector',nargs='+',choices=list(CACHE),required=True); ap.add_argument('--resume',action='store_true'); a=ap.parse_args()
 outdir=L2/'stage2_raw_vus_per_series'; outdir.mkdir(exist_ok=True)
 for det in a.detector:
  out=outdir/f'{det}.csv'; rows=[]
  if a.resume and out.exists():
   try: rows=pd.read_csv(out).to_dict('records')
   except Exception: rows=[]
  done={str(r.get('series_id')) for r in rows if r.get('status','PASS')=='PASS' and np.isfinite(float(r.get('VUS_PR',np.nan)))}
  rows=[r for r in rows if str(r.get('series_id')) in done]
  todo=[f for f in FILES if f not in done]
  print(f'[{det}] start {len(done)}/{len(FILES)} remaining={len(todo)}',flush=True); t0=time.time()
  for k,f in enumerate(todo,1):
   t=time.time()
   try:
    rows.append(one(det,f)); status='PASS'; err=''
   except Exception as e:
    rows.append({'detector':det,'series_id':f,'status':'FAIL','error':repr(e)}); status='FAIL'; err=repr(e)
   # checkpoint after every series, so interruption loses at most one row
   pd.DataFrame(rows).drop_duplicates('series_id',keep='last').set_index('series_id').reindex(FILES).reset_index().to_csv(out,index=False)
   elapsed=time.time()-t0; rate=k/max(elapsed,1e-9); eta=(len(todo)-k)/rate
   print(f'[{det}] {len(done)+k}/{len(FILES)} Series: {f} Status: {status} Runtime: {time.time()-t:.1f}s Elapsed: {elapsed/60:.1f}m ETA: {eta/60:.1f}m'+((' Error: '+err) if err else ''),flush=True)
  final=pd.DataFrame(rows).drop_duplicates('series_id',keep='last').set_index('series_id').reindex(FILES).reset_index(); final.to_csv(out,index=False)
  good=final[final.status=='PASS']
  print(f'[{det}] DONE pass={len(good)}/{len(FILES)} macro_raw_vus={good.VUS_PR.mean() if len(good) else float("nan"):.12f}',flush=True)

if __name__=='__main__': main()
