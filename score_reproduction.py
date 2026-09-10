"""Gate R0：验证 TSB-AD wrapper point-wise score 与官方 VUS-PR 的一致性。"""
from pathlib import Path
import time, json, traceback
import numpy as np
import pandas as pd
from TSB_AD import model_wrapper as mw
from vus_eval.basic_metrics import generate_curve

ROOT=Path(__file__).resolve().parent; DATA=ROOT/'Datasets'/'TSB-AD-U'; OUT=ROOT/'layer2_results'; CACHE=OUT/'detector_scores'
CACHE.mkdir(parents=True,exist_ok=True)
META=['file','ts_len','anomaly_len','num_anomaly','avg_anomaly_len','anomaly_ratio','point_anomaly','seq_anomaly']
RUNNERS={'Sub-PCA':lambda x: mw.run_Sub_PCA(x[:,None]),'POLY':lambda x: mw.run_POLY(x[:,None]),'KShapeAD':lambda x: mw.run_KShapeAD(x)}

def vus(score,label):
    *_, auc, ap=generate_curve(label.astype(int),score.astype(float),100,'opt',250)
    return float(ap)

def select_files(ref,n=10):
    # 覆盖短、中、长序列及点/序列异常；按长度分位点抽样。
    r=ref.sort_values('ts_len').reset_index(drop=True)
    pos=np.linspace(0,len(r)-1,n).round().astype(int)
    return r.iloc[np.unique(pos)].copy()

def main(n=10,detectors=None):
    ref=pd.read_csv(ROOT/'uni_vuspr.csv'); sub=select_files(ref,n)
    detectors=detectors or list(RUNNERS)
    rows=[]
    for det in detectors:
        dcache=CACHE/det; dcache.mkdir(exist_ok=True)
        for _,meta in sub.iterrows():
            f=meta['file']; path=DATA/f; t0=time.time()
            try:
                d=pd.read_csv(path).dropna(); x=d.iloc[:,0].to_numpy(float); y=d.Label.to_numpy(int)
                sd=x.std(); x=(x-x.mean())/(sd if sd>0 else 1.)
                out=dcache/(f+'.npy')
                if out.exists():
                    score=np.load(out); runtime=0.; cached=True
                else:
                    score=np.asarray(RUNNERS[det](x),float).ravel(); runtime=time.time()-t0; cached=False
                    if len(score)==len(y) and np.isfinite(score).all():
                        tmp=out.with_suffix('.tmp.npy'); np.save(tmp,score); tmp.replace(out)
                rec={'detector':det,'series_id':f,'length_y':len(y),'length_score':len(score),
                     'finite_ratio':float(np.isfinite(score).mean()),'official_vus':float(meta[det]),
                     'recomputed_vus':np.nan,'abs_diff':np.nan,'score_min':float(np.nanmin(score)),
                     'score_max':float(np.nanmax(score)),'runtime_sec':runtime,'cached':cached,'error':''}
                if len(score)==len(y) and np.isfinite(score).all():
                    rec['recomputed_vus']=vus(score,y); rec['abs_diff']=abs(rec['recomputed_vus']-rec['official_vus'])
                rows.append(rec); print(det,f,'len',len(score),'official',rec['official_vus'],'recomputed',rec['recomputed_vus'],'diff',rec['abs_diff'],'sec',round(runtime,2),flush=True)
            except Exception as e:
                rows.append({'detector':det,'series_id':f,'length_y':len(y) if 'y' in locals() else -1,'length_score':-1,'finite_ratio':0.,'official_vus':float(meta[det]),'recomputed_vus':np.nan,'abs_diff':np.nan,'score_min':np.nan,'score_max':np.nan,'runtime_sec':time.time()-t0,'cached':False,'error':repr(e)})
                traceback.print_exc()
    R=pd.DataFrame(rows); R.to_csv(OUT/'score_reproduction.csv',index=False)
    summary=R.groupby('detector').agg(n=('series_id','size'),length_fail=('length_score',lambda x:int((x<=0).sum())),finite_min=('finite_ratio','min'),mean_abs_diff=('abs_diff','mean'),max_abs_diff=('abs_diff','max'),mean_runtime=('runtime_sec','mean')).reset_index()
    summary.to_csv(OUT/'score_reproduction_summary.csv',index=False)
    print(summary.to_string(index=False))

if __name__=='__main__': main()
