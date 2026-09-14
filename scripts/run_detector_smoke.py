"""Three-series pinned smoke test before an expensive detector sweep."""
from __future__ import annotations
import argparse, importlib, json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_detector_sweep import WRAPPERS, load, sha
from vus_eval.basic_metrics import generate_curve
from cdu.tsb_ad_compat import find_length_rank_official_compat
SAMPLES = ['001_NAB_id_1_Facility_tr_1007_1st_2014.csv','141_MSL_id_2_Sensor_tr_500_1st_550.csv','179_SMD_id_2_Facility_tr_5925_1st_17580.csv']

def main():
    p=argparse.ArgumentParser(); p.add_argument('--detector',required=True,choices=WRAPPERS); p.add_argument('--seed',type=int,default=2024); p.add_argument('--device',default=None,help='recorded device hint; TSB-AD selects device internally'); a=p.parse_args()
    module=importlib.import_module(WRAPPERS[a.detector]); rows=[]
    for filename in SAMPLES:
        started=time.time(); score1=score2=np.array([])
        try:
            train,test,label=load(filename); kwargs={'profile':a.detector} if a.detector.startswith('MOMENT_') else {}
            if a.device is not None and a.detector in {'TranAD','FITS','M2N2'}: kwargs['device']=a.device
            out1=module.run_detector(train,test,seed=a.seed,**kwargs); out2=module.run_detector(train,test,seed=a.seed,**kwargs)
            if isinstance(out1,dict): score1=np.asarray(out1['score'],dtype=float).ravel(); config=out1.get('metadata',{}).get('config',{})
            else: score1,config=out1
            score2=np.asarray(out2['score'] if isinstance(out2,dict) else out2[0],dtype=float).ravel()
            length_ok=len(score1)==len(label)==len(score2); finite=float(np.isfinite(score1).mean()) if len(score1) else 0.; hash_match=sha(score1)==sha(score2)
            window=int(find_length_rank_official_compat(test,rank=1))
            vus=float(generate_curve(label,score1,window,'opt',250)[7]) if length_ok and finite==1. and np.ptp(score1)>0 else 0.0
            status='PASS' if length_ok and finite==1. and hash_match else 'FAIL'; error=''
        except Exception as exc:
            config={}; label=np.array([]); length_ok=False; finite=0.; hash_match=False; window=-1; vus=float('nan'); status='FAIL'; error=repr(exc)
        row={'detector':a.detector,'series_id':filename,'score_length':len(score1),'label_length':len(label),'score_length_match':length_ok,'finite_ratio':finite,'score_hash_run1':sha(score1),'score_hash_run2':sha(score2),'hash_match':hash_match,'window':window,'VUS_PR':vus,'seed':a.seed,'config':json.dumps(config,default=str),'runtime_sec':time.time()-started,'status':status,'error':error}
        rows.append(row); print(f'[{a.detector}] {filename} {status} runtime={row["runtime_sec"]:.1f}s',flush=True)
    out=ROOT/'layer2_results'/f'{a.detector}_smoke_test.csv'; result=pd.DataFrame(rows); result.to_csv(out,index=False); print(f'[{a.detector}] DONE pass={(result.status=="PASS").sum()}/{len(result)} {out}',flush=True)
    return 0 if (result.status=='PASS').all() else 2
if __name__=='__main__': raise SystemExit(main())
