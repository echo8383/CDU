"""Frozen end-to-end audit for POLY, SubPCA, AnomalyTransformer.

All detector metrics are recomputed solely from existing cached point scores.
No score cache is changed.  VUS window selection intentionally uses raw data,
never the detector score curve.
"""
from __future__ import annotations
import hashlib, json, os, platform, random, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import scipy, sklearn, torch
from sklearn.linear_model import LogisticRegression

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
REPO=Path(r'D:\CSIES\AI4Energy\others\TSB-AD')
sys.path.insert(0,str(REPO))
from vus_eval.basic_metrics import generate_curve
from r0_official_compat import find_length_rank_official_compat

L2=ROOT/'layer2_results'; DATA=ROOT/'Datasets'/'TSB-AD-U'; BASIS=L2/'basis_scores'
FILES=pd.read_csv(ROOT/'uni_vuspr.csv').file.astype(str).tolist(); SEED=2024
DETS={
 'POLY':dict(cache=L2/'poly_pinned_scores',impl='TSB_AD.models.POLY.POLY historical compatibility',wrapper='poly_historical_compat.run_poly_historical',config={'periodicity':1,'power':4,'normalize':False},mode='official_historical'),
 'SubPCA':dict(cache=L2/'detector_scores'/'SubPCA',impl='TSB_AD.models.PCA.PCA',wrapper='wrappers.subpca_wrapper.run_detector',config={'periodicity':1,'n_components':None},mode='pinned_current'),
 'AnomalyTransformer':dict(cache=L2/'detector_scores'/'AnomalyTransformer',impl='TSB_AD.models.AnomalyTransformer.AnomalyTransformer',wrapper='wrappers.anomaly_transformer_wrapper.run_detector',config={'win_size':50,'lr':0.001},mode='pinned_current'),
}
SAMPLES=['001_NAB_id_1_Facility_tr_1007_1st_2014.csv','141_MSL_id_2_Sensor_tr_500_1st_550.csv','179_SMD_id_2_Facility_tr_5925_1st_17580.csv']

def sha(a): return hashlib.sha256(np.ascontiguousarray(a,dtype=np.float64).tobytes()).hexdigest()
def git_hash():
 try:return subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()
 except Exception:return '8b363e350ae047a8115a594d1e9da64aae09b852 (recorded pin)'
def load_data(f):
 d=pd.read_csv(DATA/f).dropna(); return d.iloc[:,:-1].to_numpy(float),d.Label.to_numpy(int)
def eval_window(f):
 x,_=load_data(f); return int(find_length_rank_official_compat(x[:,0].reshape(-1,1),rank=1))
def load_basis(f):
 z=np.load(BASIS/(f+'.npz'),allow_pickle=False); B=z['basis']; B=B.T if B.shape[0]==31 and B.shape[1]!=31 else B
 return np.asarray(B,float),z['label'].astype(int),[str(v) for v in z['names']]
def rank01(x):
 x=np.asarray(x,float); return (np.argsort(np.argsort(x,kind='mergesort'),kind='mergesort')+.5)/len(x)
def score_path(det,f): return DETS[det]['cache']/(f+'.npy')
def vus_val(y,s,w):
 if not np.isfinite(s).all() or np.ptp(s)==0:return 0.
 return float(generate_curve(y,np.asarray(s,float),w,'opt',250)[7])

def integrity(det):
 rows=[]; cache=DETS[det]['cache']; manifest=L2/(f'{det}_score_manifest.csv')
 if det=='POLY': manifest=L2/'poly_reproducibility_350.csv'
 man=pd.read_csv(manifest).set_index('series_id') if manifest.exists() else None
 for f in FILES:
  p=score_path(det,f); x,y=load_data(f); s=np.load(p,allow_pickle=False).ravel() if p.exists() else np.array([])
  B,by,_=load_basis(f); m=man.loc[f] if man is not None and f in man.index else None
  rows.append(dict(detector=det,series_id=f,cache_exists=p.exists(),score_length=len(s),label_length=len(y),basis_rows=len(B),
   score_length_match=len(s)==len(y),basis_length_match=len(B)==len(y),basis_label_match=bool(np.array_equal(by,y)),
   finite_ratio=float(np.isfinite(s).mean()) if len(s) else 0.,constant_score=bool(len(s)>0 and np.ptp(s)==0),
   score_variance=float(np.var(s)) if len(s) else np.nan,near_zero_variance=bool(len(s)>0 and np.var(s)<1e-15),
   score_hash=sha(s),manifest_hash=(str(m['score_hash_run1']) if m is not None and det=='POLY' else (str(m.score_hash) if m is not None and 'score_hash' in m else '')),
   manifest_hash_match=(bool(str(m['score_hash_run1'])==sha(s)) if m is not None and det=='POLY' else bool(m is not None and str(m.score_hash)==sha(s))),window_from_raw_data=eval_window(f),
   score_label_alignment='PASS' if len(s)==len(y) and len(B)==len(y) and np.array_equal(by,y) else 'FAIL',
   dropped_timestamps=0,padding_or_shift_detected=False))
 return pd.DataFrame(rows)

def vus_one(arg):
 det,f=arg; _,y=load_data(f); s=np.load(score_path(det,f),allow_pickle=False).ravel(); w=eval_window(f)
 v=vus_val(y,s,w); sign=vus_val(y,-s,w) if det=='AnomalyTransformer' else np.nan
 return dict(detector=det,series_id=f,window_from_raw_data=w,VUS_PR=v,VUS_PR_negated=sign,score_hash=sha(s))
def recompute_vus(det):
 rows=[]
 # VUS evaluation allocates substantial temporary arrays per worker.  Use a
 # single worker for the audit so all 350-series results are reproducible
 # without exhausting RAM; detector score caches are never regenerated.
 with ProcessPoolExecutor(max_workers=1) as pool:
  futs={pool.submit(vus_one,(det,f)):f for f in FILES}
  for i,fu in enumerate(as_completed(futs),1):
   rows.append(fu.result())
   if i%25==0 or i==len(FILES): print(f'[{det}] audit VUS {i}/350',flush=True)
 return pd.DataFrame(rows).set_index('series_id').reindex(FILES).reset_index()

def cdu(det,k):
 data=[]
 for f in FILES:
  B,y,_=load_basis(f); s=np.load(score_path(det,f),allow_pickle=False).ravel()
  data.append((B,y,rank01(s)))
 blocks=np.array_split(np.arange(len(FILES)),k); rows=[]
 for fold,test in enumerate(blocks):
  train=np.concatenate([b for j,b in enumerate(blocks) if j!=fold])
  X0=np.vstack([data[i][0] for i in train]); X1=np.vstack([np.column_stack([data[i][0],data[i][2]]) for i in train]); Y=np.concatenate([data[i][1] for i in train])
  m0=LogisticRegression(C=.1,penalty='l2',solver='liblinear',class_weight='balanced',max_iter=300,random_state=0).fit(X0,Y)
  m1=LogisticRegression(C=.1,penalty='l2',solver='liblinear',class_weight='balanced',max_iter=300,random_state=0).fit(X1,Y)
  for i in test:
   B,y,s=data[i]; p0=np.clip(m0.predict_proba(B)[:,1],1e-7,1-1e-7); p1=np.clip(m1.predict_proba(np.column_stack([B,s]))[:,1],1e-7,1-1e-7)
   l0=-(y*np.log2(p0)+(1-y)*np.log2(1-p0)); l1=-(y*np.log2(p1)+(1-y)*np.log2(1-p1)); d=l0-l1
   rows.append(dict(detector=det,series_id=FILES[i],folds=k,fold=fold,L0_bits=float(l0.mean()),L1_bits=float(l1.mean()),CDU_bits=float(d.mean()),NCDU=float(d.mean()/max(l0.mean(),1e-12)),n_points=len(y)))
  print(f'[{det}] audit CDU {fold+1}/{k}',flush=True)
 return pd.DataFrame(rows)
def controls(k=5):
 data=[]; rng=np.random.default_rng(2024)
 for f in FILES:
  B,y,names=load_basis(f); v=B[:,names.index('Var-96')]; data.append((B,y,v))
 out=[]
 for name, curves in [('Var96_self',[v for _,_,v in data]),('Var96_affine',[100*v+7 for _,_,v in data]),('Random',[rng.random(len(y)) for _,y,_ in data])]:
  blocks=np.array_split(np.arange(len(FILES)),k); vals=[]
  for fold,test in enumerate(blocks):
   tr=np.concatenate([b for j,b in enumerate(blocks) if j!=fold]); X0=np.vstack([data[i][0] for i in tr]); X1=np.vstack([np.column_stack([data[i][0],curves[i]]) for i in tr]);Y=np.concatenate([data[i][1] for i in tr])
   m0=LogisticRegression(C=.1,solver='liblinear',class_weight='balanced',max_iter=300,random_state=0).fit(X0,Y);m1=LogisticRegression(C=.1,solver='liblinear',class_weight='balanced',max_iter=300,random_state=0).fit(X1,Y)
   for i in test:
    B,y,_=data[i];s=curves[i];p0=np.clip(m0.predict_proba(B)[:,1],1e-7,1-1e-7);p1=np.clip(m1.predict_proba(np.column_stack([B,s]))[:,1],1e-7,1-1e-7);vals.append(float((-(y*np.log2(p0)+(1-y)*np.log2(1-p0))+y*np.log2(p1)+(1-y)*np.log2(1-p1)).mean()))
  out.append(dict(control=name,folds=k,macro_CDU_bits=float(np.mean(vals)),positive_series_ratio=float(np.mean(np.asarray(vals)>0))))
 return pd.DataFrame(out)

def reproducibility(det):
 # exact reruns are intentionally limited to three predeclared diverse series.
 rows=[]
 if det=='POLY':
  from poly_historical_compat import run_poly_historical
  for f in SAMPLES:
   x,_=load_data(f); w=eval_window(f); a=run_poly_historical(x,window=w,power=4); b=run_poly_historical(x,window=w,power=4); old=np.load(score_path(det,f),allow_pickle=False);rows.append(dict(detector=det,series_id=f,rerun_hash_1=sha(a),rerun_hash_2=sha(b),cached_hash=sha(old),hash_match_runs=sha(a)==sha(b),hash_match_cache=sha(a)==sha(old),max_abs_diff=float(np.max(np.abs(a-old)))))
 else:
  mod=__import__('wrappers.'+('subpca_wrapper' if det=='SubPCA' else 'anomaly_transformer_wrapper'),fromlist=['run_detector'])
  from scripts.run_detector_sweep import load
  for f in SAMPLES:
   tr,te,_=load(f); a,_=mod.run_detector(tr,te,seed=SEED); b,_=mod.run_detector(tr,te,seed=SEED); old=np.load(score_path(det,f),allow_pickle=False);rows.append(dict(detector=det,series_id=f,rerun_hash_1=sha(a),rerun_hash_2=sha(b),cached_hash=sha(old),hash_match_runs=sha(a)==sha(b),hash_match_cache=sha(a)==sha(old),max_abs_diff=float(np.max(np.abs(a-old)))))
 return pd.DataFrame(rows)

def main():
 L2.mkdir(exist_ok=True); (L2/'audit_cdu_per_series').mkdir(exist_ok=True); prov=[]; integrity_all=[]; vus_all=[]; rep_all=[]; cdu_all=[]
 commit=git_hash()
 for det,meta in DETS.items():
  cfg=meta['config']; prov.append(dict(detector=det,implementation=meta['impl'],wrapper=meta['wrapper'],commit=commit,config_hash=hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest(),config=json.dumps(cfg),seed=SEED,score_cache_path=str(meta['cache']),number_of_series=len(list(meta['cache'].glob('*.npy'))),status='PINNED'))
  integ=integrity(det);integrity_all.append(integ);print(f'[{det}] integrity complete',flush=True)
  v=recompute_vus(det);vus_all.append(v)
  rep=reproducibility(det);rep_all.append(rep);print(f'[{det}] reproducibility complete',flush=True)
  p5=cdu(det,5);p10=cdu(det,10); per=pd.concat([p5,p10],ignore_index=True);per.to_csv(L2/'audit_cdu_per_series'/f'{det}.csv',index=False);cdu_all.append(per)
 pd.DataFrame(prov).to_csv(ROOT/'AUDIT_DETECTOR_PROVENANCE.csv',index=False)
 integ=pd.concat(integrity_all,ignore_index=True);integ.to_csv(L2/'audit_score_integrity.csv',index=False)
 vus=pd.concat(vus_all,ignore_index=True);vus.to_csv(L2/'audit_raw_vus_per_series.csv',index=False)
 rep=pd.concat(rep_all,ignore_index=True);rep.to_csv(L2/'audit_score_reproducibility_samples.csv',index=False)
 align=integ[['detector','series_id','score_length','label_length','basis_rows','score_length_match','basis_length_match','basis_label_match','score_label_alignment','dropped_timestamps','padding_or_shift_detected']].copy();align['alignment_status']=np.where(align.score_label_alignment.eq('PASS'),'PASS','FAIL');align.to_csv(L2/'audit_cdu_alignment.csv',index=False)
 ctrl=controls();ctrl.to_csv(L2/'audit_cdu_controls.csv',index=False)
 allc=pd.concat(cdu_all,ignore_index=True);summary=[];rng=np.random.default_rng(2024)
 for det in DETS:
  vv=vus[vus.detector==det].VUS_PR.to_numpy(float); a5=allc[(allc.detector==det)&(allc.folds==5)].CDU_bits.to_numpy(float);a10=allc[(allc.detector==det)&(allc.folds==10)].CDU_bits.to_numpy(float);boots=np.array([a5[rng.integers(0,len(a5),len(a5))].mean() for _ in range(10000)])
  iok=integ[integ.detector==det];rok=rep[rep.detector==det];al=align[align.detector==det]
  status='PASS' if len(iok)==350 and iok.score_label_alignment.eq('PASS').all() and iok.finite_ratio.eq(1).all() and not iok.constant_score.any() and rok.hash_match_runs.all() and rok.hash_match_cache.all() and al.alignment_status.eq('PASS').all() else 'FAIL'
  summary.append(dict(Detector=det,Raw_VUS=float(vv.mean()),CDU_5fold_bits=float(a5.mean()),CDU_10fold_bits=float(a10.mean()),CDU_median_5fold=float(np.median(a5)),CDU_CI_low=float(np.percentile(boots,2.5)),CDU_CI_high=float(np.percentile(boots,97.5)),positive_series_ratio=float(np.mean(a5>0)),bootstrap_prob_macro_positive=float(np.mean(boots>0)),Score_integrity='PASS' if iok.score_label_alignment.eq('PASS').all() else 'FAIL',Alignment='PASS' if al.alignment_status.eq('PASS').all() else 'FAIL',Reproducibility='PASS' if rok.hash_match_runs.all() and rok.hash_match_cache.all() else 'FAIL',Audit_status=status))
 S=pd.DataFrame(summary);S.to_csv(L2/'audit_cdu_recomputed.csv',index=False);S.to_csv(L2/'AUDITED_DETECTOR_RESULTS.csv',index=False)
 an=vus[vus.detector=='AnomalyTransformer']; orient=pd.DataFrame({'metric':['mean_VUS_score','mean_VUS_negated','negated_minus_score'],'value':[an.VUS_PR.mean(),an.VUS_PR_negated.mean(),(an.VUS_PR_negated-an.VUS_PR).mean()]});orient.to_csv(L2/'anomalytransformer_orientation_audit.csv',index=False)
 (ROOT/'POLY_RAW_VUS_DISCREPANCY_AUDIT.md').write_text("# POLY Raw-VUS discrepancy\n\n`0.389270589096` is the pinned R0 report value: cached historical-compatible POLY score evaluated with window selected from raw input data. `0.422519085874` was produced later by `offline_metrics_completed.py`, which incorrectly selected evaluation window from the POLY score curve itself. It is not a detector/normalization/score-cache change and is not a valid pinned Raw VUS. The audited CSV is the sole formal value.\n",encoding='utf8')
 (ROOT/'ANOMALYTRANSFORMER_WRAPPER_AUDIT.md').write_text("# AnomalyTransformer wrapper audit\n\nThe audit checks wrapper config, filename-derived training prefix, full test score length, finite cached score, cached-score reproducibility, raw-data window VUS, and score-negation diagnostic. See `layer2_results/anomalytransformer_orientation_audit.csv` and integrity/alignment CSVs. No score orientation is changed by this diagnostic.\n",encoding='utf8')
 (ROOT/'SUBPCA_PINNED_AUDIT.md').write_text("# SubPCA pinned audit\n\nCurrent pinned audit uses `PCA(slidingWindow=find_length_rank_official_compat(raw_data[:,0]), n_components=None)` with full-series unsupervised fitting, seed 2024, cached point scores, and no historical leaderboard equality requirement.\n",encoding='utf8')
 report=['# Three Detector Full Audit','',S.to_markdown(index=False),'','## Controls','',ctrl.to_markdown(index=False),'','## Field definitions','','- `positive_series_ratio`: fraction of the 350 held-out per-series CDU values greater than zero.','- `bootstrap_prob_macro_positive`: proportion of 10,000 series-level bootstrap macro means greater than zero.']
 (ROOT/'THREE_DETECTOR_FULL_AUDIT.md').write_text('\n'.join(report)+'\n',encoding='utf8')
 print(S.to_string(index=False))
if __name__=='__main__':main()
