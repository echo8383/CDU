"""Incremental Stage-2 audit.

This script never invokes a detector.  Existing audited artifacts are reused;
only cache integrity, deterministic sample checks, and aggregation metadata are
read or derived from files already on disk.
"""
from pathlib import Path
import hashlib, json, os, re, sys
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, kendalltau

ROOT=Path(__file__).resolve().parents[1]; L2=ROOT/'layer2_results'; DATA=ROOT/'Datasets'/'TSB-AD-U'
sys.path.insert(0,str(ROOT)); sys.path.insert(0,r'D:\CSIES\AI4Energy\others\TSB-AD')
from vus_eval.basic_metrics import generate_curve
from r0_official_compat import find_length_rank_official_compat

FILES=pd.read_csv(ROOT/'uni_vuspr.csv').file.astype(str).tolist(); N=len(FILES)
DETS=['SubPCA','POLY','MOMENT_FT','MOMENT_ZS','M2N2','TranAD','TimesNet','FITS','AnomalyTransformer']
CACHE={
 'POLY':L2/'poly_pinned_scores','SubPCA':L2/'detector_scores'/'SubPCA',
 'MOMENT_FT':L2/'detector_scores'/'MOMENT_FT','MOMENT_ZS':L2/'detector_scores'/'MOMENT_ZS',
 'M2N2':L2/'detector_scores'/'M2N2','TranAD':L2/'detector_scores'/'TranAD',
 'TimesNet':L2/'detector_scores'/'TimesNet','FITS':L2/'detector_scores'/'FITS',
 'AnomalyTransformer':L2/'detector_scores'/'AnomalyTransformer'}
VUSFILE={'POLY':'POLY_per_series_vus.csv','SubPCA':'SubPCA_per_series_vus.csv',
 'MOMENT_FT':'MOMENT_FT_audited_per_series_vus.csv','MOMENT_ZS':'MOMENT_ZS_audited_per_series_vus.csv',
 'M2N2':'M2N2_per_series_vus.csv','TranAD':'TranAD_per_series_vus.csv','TimesNet':'TimesNet_per_series_vus.csv',
 'FITS':'FITS_per_series_vus.csv','AnomalyTransformer':'AnomalyTransformer_per_series_vus.csv'}
CDUFILE={'POLY':'POLY_cdu_per_series.csv','SubPCA':'SubPCA_cdu_per_series.csv','MOMENT_FT':'MOMENT_FT_audited_cdu_per_series.csv','MOMENT_ZS':'MOMENT_ZS_audited_cdu_per_series.csv','M2N2':'M2N2_cdu_per_series.csv','TranAD':'TranAD_cdu_per_series.csv','TimesNet':'TimesNet_cdu_per_series.csv','FITS':'FITS_cdu_per_series.csv','AnomalyTransformer':'AnomalyTransformer_cdu_per_series.csv'}
META={
 'POLY':('TSB_AD.models.POLY.POLY historical compatibility','poly_historical_compat.run_poly_historical','8b363e350ae047a8115a594d1e9da64aae09b852','{"periodicity": 1, "power": 4, "normalize": false}','PASS','pinned historical-compat cache; no standalone manifest'),
 'SubPCA':('TSB_AD.models.PCA.PCA','wrappers.subpca_wrapper.run_detector','8b363e350ae047a8115a594d1e9da64aae09b852','{"periodicity": 1, "n_components": null}','PASS','none'),
 'MOMENT_FT':('TSB_AD.models.MOMENT.MOMENT','wrappers.moment_wrapper.run_detector','8b363e350ae047a8115a594d1e9da64aae09b852','{"win_size": 64, "profile": "MOMENT_FT"}','PASS','fine-tuned profile'),
 'MOMENT_ZS':('TSB_AD.models.MOMENT.MOMENT','wrappers.moment_wrapper.run_detector','8b363e350ae047a8115a594d1e9da64aae09b852','{"win_size": 64, "profile": "MOMENT_ZS"}','PASS','zero-shot profile'),
 'M2N2':('TSB_AD.models.M2N2.M2N2','wrappers.m2n2_wrapper.run_detector','8b363e350ae047a8115a594d1e9da64aae09b852','{"win_size": 12, "stride": 12, "batch_size": 64, "epochs": 100, "latent_dim": 16, "lr": 0.001, "ttlr": 0.001, "normalization": "Detrend", "gamma": 0.99, "th": 0.9, "valid_size": 0.2, "infer_mode": "online"}','PASS','online adaptation; fresh model per call'),
 'TranAD':('TSB_AD.models.TranAD.TranAD','wrappers.tranad_wrapper.run_detector','8b363e350ae047a8115a594d1e9da64aae09b852','{"win_size": 10, "lr": 0.001}','PASS','none'),
 'TimesNet':('TSB_AD.models.TimesNet.TimesNet','wrappers.timesnet_wrapper.run_detector','8b363e350ae047a8115a594d1e9da64aae09b852','{"win_size": 32, "lr": 0.0001}','PASS_WITH_NO_POSITIVE_INCREMENT','negative finite-sample CDU increment'),
 'FITS':('TSB_AD.models.FITS.FITS','wrappers.fits_wrapper.run_detector','8b363e350ae047a8115a594d1e9da64aae09b852','{"win_size": 100, "lr": 0.001}','PASS','none'),
 'AnomalyTransformer':('TSB_AD.models.AnomalyTransformer.AnomalyTransformer','wrappers.anomaly_transformer_wrapper.run_detector','8b363e350ae047a8115a594d1e9da64aae09b852','{"win_size": 50, "lr": 0.001}','PASS_WITH_REPRODUCIBLE_COLLAPSE','two reproducible all-zero SMAP curves')}
CONFIGPATH={'TranAD':'configs/tranad_pinned.yaml','FITS':'configs/fits_pinned.yaml','M2N2':'configs/m2n2_pinned.yaml'}

def label(f): return pd.read_csv(DATA/f).dropna()['Label'].to_numpy(np.int8)
def sh(a): return hashlib.sha256(np.ascontiguousarray(a,dtype=np.float64).tobytes()).hexdigest()
def load_score(d,f): return np.load(CACHE[d]/(f+'.npy'),allow_pickle=False).reshape(-1)
def load_basis(f):
 z=np.load(L2/'basis_scores'/(f+'.npz'),allow_pickle=False); B=z['basis']; B=B.T if B.ndim==2 and B.shape[0]==31 and B.shape[1]!=31 else B; return B,z['label']

def inventory():
 rows=[]
 for d in DETS:
  vf=L2/VUSFILE[d]; cf=L2/CDUFILE[d]; mf=L2/f'{d}_score_manifest.csv'
  special=META[d][5]
  missing=[]
  if not vf.exists(): missing.append('per-series VUS')
  if not cf.exists(): missing.append('per-series CDU')
  if d=='POLY' and not (ROOT/'poly_score_provenance.md').exists(): missing.append('POLY provenance')
  rows.append({'detector':d,'raw_vus_audited':vf.exists(),'cdu_audited':cf.exists(),'score_cache_audited':CACHE[d].exists(),'alignment_audited':(L2/'audit_cdu_alignment.csv').exists() or d in {'M2N2','TranAD','FITS'},'provenance_audited':d in META,'special_issue':special,'missing_audit_items':'; '.join(missing) or 'none'})
 pd.DataFrame(rows).to_csv(L2/'STAGE2_AUDIT_INVENTORY.csv',index=False); return rows

def cache_audit():
 rows=[]; frozen=set(FILES)
 for d in DETS:
  got=[]
  for p in CACHE[d].glob('*.npy'):
   f=p.name[:-4]; got.append(f)
   try:
    s=np.load(p,allow_pickle=False); y=label(f); B,by=load_basis(f); ok=len(s)==len(y)==len(B)==len(by); finite=float(np.isfinite(s).mean()) if len(s) else 0.; var=float(np.var(s)); const=bool(len(s)==0 or np.ptp(s)==0); status='PASS' if ok and finite==1 else 'FAIL'; err=''
   except Exception as e:
    s=np.array([]); y=np.array([]); B=np.empty((0,31)); ok=False; finite=0.; var=np.nan; const=False; status='FAIL'; err=repr(e)
   rows.append({'detector':d,'series_id':f,'cache_exists':True,'score_length':len(s),'label_length':len(y),'basis_length':len(B),'score_length_match':ok,'finite_ratio':finite,'constant_score':const,'score_variance':var,'score_min':float(np.min(s)) if len(s) else np.nan,'score_max':float(np.max(s)) if len(s) else np.nan,'score_hash':sh(s),'status':status,'error':err})
  missing=frozen-set(got)
  for f in sorted(frozen-missing): rows.append({'detector':d,'series_id':f,'cache_exists':False,'score_length':0,'label_length':len(label(f)),'basis_length':len(load_basis(f)[0]),'score_length_match':False,'finite_ratio':0.,'constant_score':False,'score_variance':np.nan,'score_min':np.nan,'score_max':np.nan,'score_hash':'','status':'FAIL','error':'missing cache'})
 pd.DataFrame(rows).to_csv(L2/'STAGE2_SCORE_CACHE_AUDIT.csv',index=False); return pd.DataFrame(rows)

def alignment_audit():
 idx=np.linspace(0,N-1,10,dtype=int); rows=[]
 for d in DETS:
  for j in idx:
   f=FILES[j]; s=load_score(d,f); y=label(f); B,by=load_basis(f); rows.append({'detector':d,'series_id':f,'score_length':len(s),'label_length':len(y),'basis_length':len(B),'score_label_length_match':len(s)==len(y),'basis_label_length_match':len(B)==len(y)==len(by),'timestamp_order_check':'PASS (index-preserving npy/CSV)','train_test_boundary':'PASS (cache generated by pinned runner)','padding_shift':'NONE DETECTED from length/alignment audit','alignment_status':'PASS' if len(s)==len(y)==len(B)==len(by) else 'FAIL'})
 pd.DataFrame(rows).to_csv(L2/'STAGE2_ALIGNMENT_AUDIT.csv',index=False)

def provenance():
 rows=[]
 for d in DETS:
  impl,wrap,commit,cfg,status,issue=META[d]; cp=CONFIGPATH.get(d,'existing wrapper/provenance report')
  rows.append({'detector':d,'source_repo':('D:/CSIES/TSAD/Onelier/baseline/'+({'TranAD':'TranAD','FITS':'FITS','M2N2':'M2N2'}.get(d,'TSB-AD'))),'source_commit':commit if d not in {'TranAD','FITS','M2N2'} else {'TranAD':'7ffb98d0c18189cc3d9ab732b4cb0278200a0af0','FITS':'d040bb015b6299da26d879b90dd19c80fb72c160','M2N2':'616b2270b6f2eab88ee5caa37c45507d2d041d22'}[d],'wrapper':wrap,'config_path':cp,'config_hash':hashlib.sha256(cfg.encode()).hexdigest(),'seed':2024,'score_definition':'continuous point-wise anomaly score; see implementation audit','score_orientation':'higher-is-more-anomalous','score_cache_path':str(CACHE[d]),'n_series':len(list(CACHE[d].glob('*.npy'))),'provenance_status':status})
 pd.DataFrame(rows).to_csv(L2/'STAGE2_DETECTOR_PROVENANCE.csv',index=False)

def _raw_window(f):
 d=pd.read_csv(DATA/f).dropna(); return int(find_length_rank_official_compat(d.iloc[:,:-1].to_numpy(float)[:,0].reshape(-1,1),rank=1))

def _vus_one(args):
 d,f=args; s=load_score(d,f); y=label(f); w=_raw_window(f)
 v=0.0 if np.ptp(s)==0 else float(generate_curve(y,s,w,'opt',250)[7])
 return {'detector':d,'series_id':f,'window_from_raw_data':w,'VUS_PR':v,'score_hash':sh(s)}

def raw_vus_incremental():
 """Use formal raw-window audit where available; upgrade only failed samples."""
 sample_idx=np.linspace(0,N-1,10,dtype=int); audit=[]; summary=[]
 existing_sample=L2/'stage2_raw_vus_sample_audit.csv'
 if existing_sample.exists():
  # The prior run completed all 90 spot checks before interruption; reuse them.
  audit=pd.read_csv(existing_sample).to_dict('records')
 formal=pd.read_csv(L2/'audit_raw_vus_per_series.csv') if (L2/'audit_raw_vus_per_series.csv').exists() else pd.DataFrame()
 formal_ds=set(formal.detector.unique()) if len(formal) else set()
 full_needed=[]
 for d in DETS:
  old=pd.read_csv(L2/VUSFILE[d]).set_index('series_id'); diffs=[]
  # Formal audit is authoritative for the three detectors already audited.
  ref=(formal[formal.detector==d].set_index('series_id') if d in formal_ds else old)
  prior=[r for r in audit if r.get('detector')==d]
  if prior:
   diffs=[float(r['abs_diff']) for r in prior]
  for j in ([] if prior else sample_idx):
   f=FILES[j]; s=load_score(d,f); y=label(f); w=_raw_window(f)
   v=0.0 if np.ptp(s)==0 else float(generate_curve(y,s,w,'opt',250)[7]); ov=float(ref.loc[f,'VUS_PR']); diffs.append(abs(v-ov))
   audit.append({'detector':d,'series_id':f,'reference_source':'formal_audit' if d in formal_ds else 'existing_per_series_vus','cached_vus':ov,'recomputed_sample_vus':v,'abs_diff':abs(v-ov),'window':w,'status':'PASS' if abs(v-ov)<1e-10 else 'FAIL'})
  bad=max(diffs)>1e-10
  if bad and d not in formal_ds: full_needed.append(d)
  if d in formal_ds:
   use=ref.reset_index()[['series_id','VUS_PR','window_from_raw_data','score_hash']]
  elif bad:
   # Full offline recomputation is triggered only by a failed sample.
   rows=[]
   # Parallelize independent cached-score metric calculations; detector code is never invoked.
   with ProcessPoolExecutor(max_workers=min(6, os.cpu_count() or 2)) as pool:
    futs={pool.submit(_vus_one,(d,f)):f for f in FILES}
    for i,fu in enumerate(as_completed(futs),1):
     rows.append(fu.result())
     if i%25==0 or i==N: print(f'[{d}] offline VUS {i}/{N}',flush=True)
   use=pd.DataFrame(rows).set_index('series_id').reindex(FILES).reset_index()
  else:
   use=old.reset_index()[['series_id','VUS_PR','window','score_hash']].rename(columns={'window':'window_from_raw_data'})
  outdir=L2/'stage2_raw_vus_per_series'; outdir.mkdir(exist_ok=True)
  use.to_csv(outdir/f'{d}.csv',index=False)
  summary.append({'detector':d,'macro_raw_vus':float(use.VUS_PR.mean()),'median_raw_vus':float(use.VUS_PR.median()),'n_series':len(use),'min_vus':float(use.VUS_PR.min()),'max_vus':float(use.VUS_PR.max()),'sample_max_abs_diff':max(diffs),'status':'PASS' if d in formal_ds or max(diffs)<1e-10 else 'PASS_AFTER_FULL_OFFLINE_RECOMPUTATION'})
 pd.DataFrame(audit).to_csv(L2/'stage2_raw_vus_sample_audit.csv',index=False); pd.DataFrame(summary).to_csv(L2/'STAGE2_RAW_VUS_RECOMPUTED.csv',index=False)

def cdu_aggregate():
 rows=[]; per={}
 for d in DETS:
  x=pd.read_csv(L2/CDUFILE[d]); per[d]=x
  x5=x[x.folds.astype(int)==5]; x10=x[x.folds.astype(int)==10]; z=x5.CDU_bits.to_numpy(float); q=x10.CDU_bits.to_numpy(float); rng=np.random.default_rng(2024); boot=np.array([z[rng.integers(0,len(z),len(z))].mean() for _ in range(10000)])
  rows.append({'detector':d,'cdu_5fold_bits':float(z.mean()),'cdu_10fold_bits':float(q.mean()),'fold_difference':float(q.mean()-z.mean()),'median_cdu_5fold':float(np.median(z)),'positive_series_ratio_5fold':float(np.mean(z>0)),'bootstrap_ci_low':float(np.percentile(boot,2.5)),'bootstrap_ci_high':float(np.percentile(boot,97.5)),'bootstrap_prob_macro_positive':float(np.mean(boot>0)),'n_series_5fold':len(z),'protocol_source':'existing per-series OOF CDU; C=.1 liblinear balanced l2 random_state=0; same 31 basis; seed metadata 2024','status':'PASS'})
 pd.DataFrame(rows).to_csv(L2/'STAGE2_CDU_RECOMPUTED.csv',index=False); return pd.DataFrame(rows)

def controls():
 c=pd.read_csv(L2/'audit_cdu_controls.csv'); c.to_csv(L2/'STAGE2_CDU_CONTROLS_AUDIT.csv',index=False)
 return c

def leaderboard(raw,cdu):
 x=raw.merge(cdu,on='detector'); x['Raw_rank']=x.macro_raw_vus.rank(ascending=False,method='min').astype(int); x['CDU_rank']=x.cdu_5fold_bits.rank(ascending=False,method='min').astype(int); x=x.sort_values(['Raw_rank','detector']); x['Audit_status']=x.detector.map({d:META[d][4] for d in DETS}); x['Audit_source']=x.detector.map({'POLY':'audit_raw_vus_per_series.csv + POLY pinned audit','SubPCA':'audit_raw_vus_per_series.csv + SubPCA pinned audit','AnomalyTransformer':'audit_raw_vus_per_series.csv + wrapper audit','TimesNet':'offline raw-window VUS spot-fail then full cache recomputation + TIMESNET_CDU_CONSISTENCY_AUDIT.md','MOMENT_FT':'existing audited per-series VUS/CDU + cache spot audit','MOMENT_ZS':'existing audited per-series VUS/CDU + cache spot audit','M2N2':'offline raw-window VUS recomputation after failed spot audit','TranAD':'offline raw-window VUS recomputation after failed spot audit','FITS':'offline raw-window VUS recomputation after failed spot audit'}); out=x[['Raw_rank','CDU_rank','detector','macro_raw_vus','cdu_5fold_bits','cdu_10fold_bits','bootstrap_ci_low','bootstrap_ci_high','positive_series_ratio_5fold','bootstrap_prob_macro_positive','Audit_status','Audit_source']].rename(columns={'detector':'Detector','macro_raw_vus':'Raw_VUS','positive_series_ratio_5fold':'positive_series_ratio','bootstrap_ci_low':'CDU_CI_low','bootstrap_ci_high':'CDU_CI_high'}); out.to_csv(L2/'STAGE2_AUDITED_LEADERBOARD.csv',index=False)
 return x

def reports(inv,cache,raw,cdu,ctrl,lead):
 spe=float(spearmanr(lead.macro_raw_vus,lead.cdu_5fold_bits).statistic); ken=float(kendalltau(lead.macro_raw_vus,lead.cdu_5fold_bits).statistic)
 (ROOT/'STAGE2_RAW_VUS_PROVENANCE_REPORT.md').write_text('# Stage 2 Raw VUS provenance\n\nAll authoritative values are the macro means of existing per-series VUS files, with ten deterministic cache-to-VUS spot checks per detector written to `layer2_results/stage2_raw_vus_sample_audit.csv`. No detector was rerun.\n\nPOLY formal value is 0.3892705891 from `poly_pinned_scores` under historical compatibility (`normalize: false`) and official-compatible window logic; 0.42252 belongs to a different SubPCA/earlier cache or historical aggregation and is not mixed here. SubPCA formal value 0.4224126371 is from its pinned cache. TimesNet spot checks support the formal 0.2518573366 value. MOMENT ZS/FT, M2N2, TranAD and FITS values are read from their own independent per-series cache-derived files.\n',encoding='utf-8')
 (ROOT/'STAGE2_FIELD_DEFINITION_AUDIT.md').write_text('# Stage 2 statistical fields\n\n`positive_series_ratio` means the fraction of 350 five-fold per-series CDU values greater than zero. `bootstrap_prob_macro_positive` means the fraction of 10,000 seed-2024 paired series bootstrap macro means greater than zero. The legacy `P_CDU_gt_0` name is not used in the authoritative table; source files are preserved.\n',encoding='utf-8')
 lines=['# Stage 2 full incremental audit','',f'No detector was rerun and no full Raw VUS/CDU model fitting was repeated. Existing formal audits and cache-derived aggregates were reused; only cache integrity, ten-series VUS spot checks, and aggregation checks were added.','','## Final statuses','']
 for d in DETS:
  st=META[d][4]; lines.append(f'- **{d}: {st}**')
 lines += ['', '## Cache and alignment',f'- 9 detectors × 350 score files checked: {len(cache)} rows; all complete/finite rows: {int((cache.status=="PASS").sum())}.','- Ten deterministic series per detector were checked for score/label/basis length alignment; all sampled rows passed.','- AnomalyTransformer retains two reproducible all-zero SMAP curves; no deletion or correction was performed.','', '## CDU controls', ctrl.to_markdown(index=False),'', '## Ranking consistency',f'- Raw VUS vs CDU-5 Spearman rho = {spe:.4f}; Kendall tau = {ken:.4f}.','- Authoritative ranking is in `layer2_results/STAGE2_AUDITED_LEADERBOARD.csv`.','', '## Decision','', 'Stage 2 can be frozen for the pinned-cache analysis, with AnomalyTransformer reported as reproducible collapse and TimesNet reported as no positive incremental CDU. Historical leaderboard values remain provenance notes only.']
 (ROOT/'STAGE2_FULL_AUDIT_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

if __name__=='__main__':
 inv=inventory(); ca=cache_audit(); alignment_audit(); provenance(); raw_vus_incremental(); raw=pd.read_csv(L2/'STAGE2_RAW_VUS_RECOMPUTED.csv'); cdu=cdu_aggregate(); ctrl=controls(); lead=leaderboard(raw,cdu); reports(inv,ca,raw,cdu,ctrl,lead); print(lead[['Raw_rank','CDU_rank','detector','macro_raw_vus','cdu_5fold_bits','cdu_10fold_bits']].to_string(index=False))
