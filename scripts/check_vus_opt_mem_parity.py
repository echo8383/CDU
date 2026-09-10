from pathlib import Path
import sys,time
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1]; L2=ROOT/'layer2_results'; DATA=ROOT/'Datasets'/'TSB-AD-U'
sys.path.insert(0,str(ROOT))
from vus_eval.basic_metrics import generate_curve
from vus_eval.fast_vus import vus_pr_exact_vectorized, vus_pr_exact_sparse
from r0_official_compat import find_length_rank_official_compat
DETS=['SubPCA','POLY','MOMENT_FT','MOMENT_ZS','M2N2','TranAD','TimesNet','FITS','AnomalyTransformer']
CACHE={d:(L2/'poly_pinned_scores' if d=='POLY' else L2/'detector_scores'/d) for d in DETS}
files=pd.read_csv(ROOT/'uni_vuspr.csv').file.astype(str).tolist()
tests=[files[0],files[2],files[10]]
combos=[('SubPCA',),('SubPCA','M2N2'),('POLY','TranAD','FITS'),('MOMENT_FT','TimesNet','FITS','AnomalyTransformer')]
rows=[]
for f in tests:
 d=pd.read_csv(DATA/f).dropna(); y=d.Label.to_numpy(int); x=d.iloc[:,:-1].to_numpy(float); w=int(find_length_rank_official_compat(x[:,0].reshape(-1,1),rank=1))
 ranks={}
 for det in DETS:
  s=np.load(CACHE[det]/(f+'.npy')).reshape(-1); ranks[det]=(np.argsort(np.argsort(s,kind='mergesort'),kind='mergesort')+.5)/len(s)
 for c in combos:
  s=np.mean([ranks[z] for z in c],axis=0); t=time.time(); a=float(generate_curve(y,s,w,'opt',250)[7]); ta=time.time()-t; t=time.time(); b=float(generate_curve(y,s,w,'opt_mem',250)[7]); tb=time.time()-t
  t=time.time(); fast=vus_pr_exact_vectorized(y,s,w,250); tf=time.time()-t
  t=time.time(); sparse=vus_pr_exact_sparse(y,s,w,250); ts=time.time()-t
  rows.append({'series_id':f,'combo':'+'.join(c),'window':w,'opt':a,'opt_mem':b,'fast':fast,'sparse':sparse,'abs_diff':abs(a-b),'fast_abs_diff':abs(a-fast),'sparse_abs_diff':abs(a-sparse),'opt_seconds':ta,'opt_mem_seconds':tb,'fast_seconds':tf,'sparse_seconds':ts,'speedup':ta/max(ts,1e-12)})
  print(rows[-1],flush=True)
pd.DataFrame(rows).to_csv(ROOT/'stage3_results'/'VUS_OPT_MEM_PARITY.csv',index=False)
