"""Targeted diagnostics for the two already-flagged zero-score series."""
from pathlib import Path
import json, sys, time
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'Datasets'/'TSB-AD-U'; L2=ROOT/'layer2_results'
sys.path.insert(0,str(ROOT)); sys.path.insert(0,r'D:\CSIES\AI4Energy\others\TSB-AD')
from wrappers.anomaly_transformer_wrapper import run_detector

TARGETS=['531_SMAP_id_1_Sensor_tr_1811_1st_4510.csv','536_SMAP_id_6_Sensor_tr_2160_1st_5600.csv']

def main():
    rows=[]
    for f in TARGETS:
        d=pd.read_csv(DATA/f).dropna(); x=d.iloc[:,:-1].to_numpy(float); cut=int(f.split('_tr_')[1].split('_')[0]); tr=x[:cut]
        old=np.load(L2/'detector_scores'/'AnomalyTransformer'/(f+'.npy'),allow_pickle=False)
        t=time.time(); s,cfg=run_detector(tr,x,seed=2024); dt=time.time()-t
        rows.append({'series_id':f,'train_points':len(tr),'full_points':len(x),'train_std':float(tr.std()),'train_min':float(tr.min()),'train_max':float(tr.max()),'full_std':float(x.std()),'cached_unique':int(np.unique(old).size),'rerun_unique':int(np.unique(s).size),'rerun_min':float(np.min(s)),'rerun_max':float(np.max(s)),'rerun_std':float(np.std(s)),'max_abs_cached_rerun':float(np.max(np.abs(old-s))),'config':json.dumps(cfg,sort_keys=True),'runtime_sec':dt})
        print(rows[-1],flush=True)
    pd.DataFrame(rows).to_csv(L2/'anomalytransformer_collapse_diagnostic.csv',index=False)

if __name__=='__main__': main()
