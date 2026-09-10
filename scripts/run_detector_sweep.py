"""One-cache-only pinned detector sweep with resume and visible progress.

It intentionally does not compute VUS, Hard-VUS, or CDU.  Those metrics must
be computed later from the exact same saved .npy files.
"""
from __future__ import annotations
import argparse, hashlib, importlib, json, os, platform, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
import scipy, sklearn, torch

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DATA=ROOT/'Datasets'/'TSB-AD-U'; OUT=ROOT/'layer2_results'/'detector_scores'
REF=pd.read_csv(ROOT/'uni_vuspr.csv'); FILES=REF.file.tolist(); SEED_DEFAULT=2024
WRAPPERS={'SubPCA':'wrappers.subpca_wrapper','AnomalyTransformer':'wrappers.anomaly_transformer_wrapper','TimesNet':'wrappers.timesnet_wrapper','MOMENT_ZS':'wrappers.moment_wrapper','MOMENT_FT':'wrappers.moment_wrapper','TranAD':'wrappers.tranad_wrapper','FITS':'wrappers.fits_wrapper','M2N2':'wrappers.m2n2_wrapper'}

def sha(a): return hashlib.sha256(np.ascontiguousarray(a,dtype=np.float64).tobytes()).hexdigest()
def family(f): return f.split('_')[1]
def config_hash(cfg): return hashlib.sha256(json.dumps(cfg,sort_keys=True,default=str).encode()).hexdigest()
def invoke(module, train, test, det, seed, device=None):
    kwargs={'profile':det} if det.startswith('MOMENT_') else {}
    if device is not None and det in {'TranAD','FITS','M2N2'}:
        kwargs['device']=device
    result=module.run_detector(train,test,seed=seed,**kwargs)
    if isinstance(result, dict):
        return np.asarray(result['score'],dtype=float).ravel(), result.get('metadata',{}).get('config',{}), result.get('metadata',{})
    score,cfg=result
    return np.asarray(score,dtype=float).ravel(), cfg, {}
def train_cut(f): return int(Path(f).stem.split('_')[-3])
def load(f):
    d=pd.read_csv(DATA/f).dropna(); x=d.iloc[:,:-1].values.astype(float); y=d['Label'].astype(int).to_numpy(); cut=train_cut(f)
    return x[:cut],x,y
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--detector',required=True,choices=WRAPPERS); ap.add_argument('--seed',type=int,default=SEED_DEFAULT); ap.add_argument('--device',default=None,help='recorded device hint; TSB-AD selects device internally'); ap.add_argument('--resume',action='store_true',help='resume is the default; flag kept for explicitness'); ap.add_argument('--retry-failed',action='store_true'); ap.add_argument('--limit',type=int); a=ap.parse_args()
    det=a.detector; mod=importlib.import_module(WRAPPERS[det]); dest=OUT/det; dest.mkdir(parents=True,exist_ok=True); manifest=ROOT/'layer2_results'/f'{det}_score_manifest.csv'
    rows=[]; completed=set()
    if manifest.exists() and manifest.stat().st_size>5:
        old=pd.read_csv(manifest); rows=old.to_dict('records')
        completed=set(old.loc[old.status=='PASS','series_id'])
        if not a.retry_failed: completed|=set(old.loc[old.status=='FAIL','series_id'])
    files=FILES[:a.limit] if a.limit else FILES; todo=[f for f in files if f not in completed]; t_all=time.time(); runtimes=[]
    print(f'[{det}] resume: completed={len(completed)} todo={len(todo)} total={len(files)} seed={a.seed}',flush=True)
    for n,f in enumerate(todo,1):
        t=time.time(); err=''; score=np.array([],float); cfg={}; meta={}; y=np.array([],dtype=int); out=dest/(f+'.npy')
        try:
            tr,te,y=load(f)
            score,cfg,meta=invoke(mod,tr,te,det,a.seed,a.device)
            length_ok=len(score)==len(y); finite=float(np.isfinite(score).mean()) if len(score) else 0.
            if not length_ok: raise ValueError(f'length score={len(score)} label={len(y)}')
            if finite!=1.: raise ValueError(f'finite_ratio={finite}')
            tmp=out.with_name(out.name+f'.{os.getpid()}.tmp')
            with open(tmp,'wb') as z: np.save(z,score)
            os.replace(tmp,out); status='PASS'
        except Exception as e:
            status='FAIL'; err=repr(e); length_ok=False; finite=0.
        runtime=time.time()-t; runtimes.append(runtime)
        ordinal=FILES.index(f)+1
        row={'detector':det,'series_index':ordinal,'total_series':len(FILES),'series_id':f,'dataset_family':family(f),'score_path':str(out),'score_length':len(score),'label_length':len(y),'score_length_match':length_ok,'finite_ratio':finite,'score_hash':sha(score),'seed':a.seed,'config':json.dumps(cfg,sort_keys=True,default=str),'config_hash':config_hash(cfg),'runtime_sec':runtime,'status':status,'error':err}
        rows=[r for r in rows if r.get('series_id')!=f]; rows.append(row); pd.DataFrame(rows).to_csv(manifest,index=False)
        remaining=len(todo)-n; eta=np.mean(runtimes)*remaining if runtimes else 0
        print(f'[{det}] {ordinal}/{len(files)} | Series: {f} | Status: {status} | Runtime: {runtime:.1f}s | PASS={sum(r.get("status")=="PASS" for r in rows)} FAIL={sum(r.get("status")=="FAIL" for r in rows)} | ETA: {eta/60:.1f}m',flush=True)
    r=pd.DataFrame(rows); scope=r[r.series_id.isin(files)]; print(f'[{det}] DONE scope={len(scope)}/{len(files)} pass={(scope.status=="PASS").sum()} fail={(scope.status=="FAIL").sum()} manifest={manifest}',flush=True)
    return 0 if len(scope)==len(files) and (scope.status=='PASS').all() else 2
if __name__=='__main__': raise SystemExit(main())
