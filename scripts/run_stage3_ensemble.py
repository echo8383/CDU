from pathlib import Path
import itertools, hashlib, json, time, argparse
import numpy as np, pandas as pd
import gc
from concurrent.futures import ProcessPoolExecutor, as_completed
from sklearn.linear_model import LogisticRegression
from scipy.stats import bootstrap
import sys
ROOT=Path(__file__).resolve().parents[1]; L2=ROOT/'layer2_results'; DATA=ROOT/'Datasets'/'TSB-AD-U'
sys.path.insert(0,str(ROOT)); sys.path.insert(0,r'D:\CSIES\AI4Energy\others\TSB-AD')
from vus_eval.basic_metrics import generate_curve
from vus_eval.fast_vus import vus_pr_exact_sparse, prepare_sparse_vus
from r0_official_compat import find_length_rank_official_compat

DETS=['SubPCA','POLY','MOMENT_FT','MOMENT_ZS','M2N2','TranAD','TimesNet','FITS','AnomalyTransformer']
DET_ORDER={d:i for i,d in enumerate(DETS)}
CACHE={'POLY':L2/'poly_pinned_scores','SubPCA':L2/'detector_scores'/'SubPCA'}
for d in DETS:
 if d not in CACHE: CACHE[d]=L2/'detector_scores'/d
REF=pd.read_csv(ROOT/'uni_vuspr.csv'); FILES=REF.file.astype(str).tolist(); N=len(FILES)

def rank01(x):
 x=np.asarray(x,float); return (np.argsort(np.argsort(x,kind='mergesort'),kind='mergesort')+.5)/len(x)
def load(f):
 d=pd.read_csv(DATA/f).dropna(); y=d.Label.to_numpy(np.int8); raw=d.iloc[:,:-1].to_numpy(float); w=int(find_length_rank_official_compat(raw[:,0].reshape(-1,1),rank=1))
 z=np.load(L2/'basis_scores'/(f+'.npz'),allow_pickle=False); B=z['basis']; B=B.T if B.ndim==2 and B.shape[0]==31 and B.shape[1]!=31 else B
 scores={det:np.load(CACHE[det]/(f+'.npy'),allow_pickle=False).reshape(-1) for det in DETS}
 return y,w,np.asarray(B,float),{d:rank01(s) for d,s in scores.items()}

class LazySeries:
 def __getitem__(self,i): return load(FILES[i])
DATA_SER=LazySeries()
def vus(y,s,w,context=None):
 s=np.asarray(s,float)
 return 0.0 if np.ptp(s)==0 else vus_pr_exact_sparse(y,s,w,250,context=context)
def ens_vus(i,combo):
 y,w,B,S=DATA_SER[i]; s=np.mean(np.vstack([S[d] for d in combo]),axis=0); return vus(y,s,w)

def combo_key(combo): return '+'.join(sorted(combo,key=DET_ORDER.get))

def all_combo_vus(args):
 i, combos=args; y,w,B,S=DATA_SER[i]; out={}; context=prepare_sparse_vus(y,w)
 for c in combos:
  s=np.mean(np.vstack([S[d] for d in c]),axis=0); out[combo_key(c)]=vus(y,s,w,context)
 return i,out

def load_cdu_data(indices):
 """Load only outer-train frozen inputs; outer-test never enters selection."""
 data={}; indices=[int(i) for i in indices]
 for pos,i in enumerate(indices,1):
  f=FILES[i]
  z=np.load(L2/'basis_scores'/(f+'.npz'),allow_pickle=False)
  B=z['basis']; B=B.T if B.ndim==2 and B.shape[0]==31 and B.shape[1]!=31 else B
  y=z['label'].astype(np.int8)
  S={d:rank01(np.load(CACHE[d]/(f+'.npy'),allow_pickle=False).reshape(-1)) for d in DETS}
  data[i]=(y,np.asarray(B,float),S)
  if pos%50==0 or pos==len(indices): print(f'conditional-CDU outer-train inputs loaded {pos}/{len(indices)}',flush=True)
 return data

def cdu_candidate_utilities(train_idx, selected, candidates, data, outer_fold, step):
 """Inner 5-fold OOF utilities; fit the shared M0 only once per inner fold."""
 blocks=np.array_split(np.asarray(train_idx),5)
 values={d:[] for d in candidates}
 for fi,test in enumerate(blocks):
  tr=np.concatenate([b for j,b in enumerate(blocks) if j!=fi])
  # One shared training matrix per fold.  Its only candidate-dependent column
  # is selected below; M0 and M1 otherwise have identical probe settings.
  names=list(selected)+list(candidates)
  X=np.vstack([np.column_stack([data[i][1]]+[data[i][2][d] for d in names]) for i in tr])
  Y=np.concatenate([data[i][0] for i in tr])
  ref_cols=list(range(31+len(selected)))
  m0=LogisticRegression(C=.1,penalty='l2',solver='liblinear',class_weight='balanced',max_iter=300,random_state=0).fit(X[:,ref_cols],Y)
  ref_losses={}
  for i in test:
   y,B,S=data[i]; xr=np.column_stack([B]+[S[d] for d in selected]); p=np.clip(m0.predict_proba(xr)[:,1],1e-7,1-1e-7)
   ref_losses[int(i)]=-(y*np.log2(p)+(1-y)*np.log2(1-p))
  for ci,cand in enumerate(candidates):
   cand_col=31+len(selected)+ci
   cols=ref_cols+[cand_col]
   m1=LogisticRegression(C=.1,penalty='l2',solver='liblinear',class_weight='balanced',max_iter=300,random_state=0).fit(X[:,cols],Y)
   for i in test:
    y,B,S=data[i]; xc=np.column_stack([B]+[S[d] for d in selected]+[S[cand]]); p=np.clip(m1.predict_proba(xc)[:,1],1e-7,1-1e-7)
    l1=-(y*np.log2(p)+(1-y)*np.log2(1-p)); values[cand].append(float((ref_losses[int(i)]-l1).mean()))
   print(f'outer fold {outer_fold+1}/5 selection K={step} inner {fi+1}/5 candidate {ci+1}/{len(candidates)} {cand}',flush=True)
  del X,Y,m0,ref_losses; gc.collect()
 return {d:float(np.mean(values[d])) for d in candidates}

def main():
 out=L2.parent/'stage3_results'; out.mkdir(exist_ok=True)
 folds=np.array_split(np.arange(N),5); pd.DataFrame({'series_id':FILES,'outer_fold':sum(([k]*len(b) for k,b in enumerate(folds)),[])}).to_csv(out/'outer_fold_assignment.csv',index=False)
 raw_lookup={}
 formal=pd.read_csv(L2/'audit_raw_vus_per_series.csv')
 for d in DETS:
  candidates=[L2/'stage2_raw_vus_per_series'/f'{d}.csv',L2/({'MOMENT_FT':'MOMENT_FT_audited_per_series_vus.csv','MOMENT_ZS':'MOMENT_ZS_audited_per_series_vus.csv'}.get(d,f'{d}_per_series_vus.csv'))]
  for p in candidates:
   if p.exists(): raw_lookup[d]=pd.read_csv(p).set_index('series_id').VUS_PR.to_dict(); break
  if d=='AnomalyTransformer': raw_lookup[d]=formal[formal.detector==d].set_index('series_id').VUS_PR.to_dict()
 results=[]; per_series_results=[]; cdu_path=[]; raw_path=[]; random_rows=[]; oracle_rows=[]; rng=np.random.default_rng(2024); cdu_data=None
 for fold,test in enumerate(folds):
  train=np.concatenate([b for j,b in enumerate(folds) if j!=fold]); means={d:np.mean([raw_lookup[d][FILES[i]] for i in train]) for d in DETS}; order=sorted(DETS,key=lambda d:(-means[d],d)); raw_sel=[]; cdu_sel=[]
  combos=[combo_key(c) for k in range(1,5) for c in itertools.combinations(DETS,k)]
  combo_tuples=[tuple(c.split('+')) for c in combos]; combo_map={}
  cache_file=out/f'ensemble_vus_fold{fold}.csv'; done=set()
  if cache_file.exists():
   old=pd.read_csv(cache_file); done=set(old.series_index.astype(int)); combo_map={int(r.series_index):{c:float(r[c]) for c in combos} for _,r in old.iterrows()}
  todo=[int(i) for i in test if int(i) not in done]
  with ProcessPoolExecutor(max_workers=6) as pool:
   futs={pool.submit(all_combo_vus,(i,combo_tuples)):i for i in todo}
   for pos,fu in enumerate(as_completed(futs),len(done)+1):
    i,m=fu.result(); combo_map[int(i)]=m
    pd.DataFrame([{'series_index':int(i),'series_id':FILES[int(i)],**m}]).to_csv(cache_file,mode='a',header=not cache_file.exists(),index=False)
    print(f'outer fold {fold+1}/5 ensemble VUS {pos}/{len(test)}',flush=True)
  def cvus(combo): return float(np.mean([combo_map[int(i)][combo_key(combo)] for i in test]))
  for k in range(1,5):
   raw_sel=order[:k]; rawv=cvus(raw_sel); raw_path.append({'fold':fold,'K':k,'selected_detectors':'+'.join(raw_sel),'test_macro_VUS':rawv})
   if k==1: cdu_sel=[order[0]]; scores={}
   else:
    rem=[d for d in DETS if d not in cdu_sel]
    if cdu_data is None: cdu_data=load_cdu_data(train)
    score_cache=out/f'conditional_utility_fold{fold}_K{k}.json'
    if score_cache.exists(): scores=json.loads(score_cache.read_text(encoding='utf-8'))
    else:
     scores=cdu_candidate_utilities(train,cdu_sel,rem,cdu_data,fold,k)
     score_cache.write_text(json.dumps(scores,sort_keys=True,indent=2),encoding='utf-8')
    best=max(rem,key=lambda d:(scores[d],d)); cdu_sel.append(best)
   cv=cvus(cdu_sel); results.append({'fold':fold,'K':k,'method':'Raw_VUS_Selection','selected_detectors':'+'.join(raw_sel),'test_macro_VUS':rawv}); results.append({'fold':fold,'K':k,'method':'CDU_Selection','selected_detectors':'+'.join(cdu_sel),'test_macro_VUS':cv})
   for i in test:
    per_series_results.append({'fold':fold,'series_id':FILES[int(i)],'K':k,'raw_selected':'+'.join(raw_sel),'cdu_selected':'+'.join(cdu_sel),'raw_test_VUS':combo_map[int(i)][combo_key(raw_sel)],'cdu_test_VUS':combo_map[int(i)][combo_key(cdu_sel)]})
   cdu_path.append({'fold':fold,'K':k,'selected_detectors':'+'.join(cdu_sel),'chosen_detector':cdu_sel[-1],'candidate_utilities':json.dumps(scores,sort_keys=True),'test_macro_VUS':cv})
  for k in (2,3,4):
   vals=[]
   for r in range(1000):
    combo=tuple(rng.choice(DETS,size=k,replace=False)); vals.append(float(np.mean([combo_map[int(i)][combo_key(combo)] for i in test])))
   random_rows.append({'fold':fold,'K':k,'mean_test_VUS':float(np.mean(vals)),'ci_low':float(np.percentile(vals,2.5)),'ci_high':float(np.percentile(vals,97.5)),'n_random':1000})
   best=[]; bestv=-1
   for combo in itertools.combinations(DETS,k):
    v=float(np.mean([combo_map[int(i)][combo_key(combo)] for i in test]));
    if v>bestv: bestv=v; best=list(combo)
   oracle_rows.append({'fold':fold,'K':k,'oracle_detectors':'+'.join(best),'oracle_test_VUS':bestv,'label':'ORACLE / NOT DEPLOYABLE'})
  print(f'outer fold {fold+1}/5 complete',flush=True)
  # Selection/evaluation checkpoints after every completed outer fold.
  pd.DataFrame(results).to_csv(out/'STAGE3_ENSEMBLE_RESULTS.csv',index=False); pd.DataFrame(per_series_results).to_csv(out/'STAGE3_ENSEMBLE_PER_SERIES.csv',index=False); pd.DataFrame(cdu_path).to_csv(out/'CDU_SELECTION_PATH.csv',index=False); pd.DataFrame(raw_path).to_csv(out/'RAW_VUS_SELECTION_PATH.csv',index=False); pd.DataFrame(random_rows).to_csv(out/'RANDOM_SELECTION_RESULTS.csv',index=False); pd.DataFrame(oracle_rows).to_csv(out/'ORACLE_UPPER_BOUND.csv',index=False)
  if cdu_data is not None:
   cdu_data=None; gc.collect()
 # Paired bootstrap over all 350 outer-test series, as preregistered.
 boot=[]
 rr=pd.DataFrame(results); ps=pd.DataFrame(per_series_results)
 for k in (2,3,4):
  z=ps[ps.K==k]; delta=(z.cdu_test_VUS-z.raw_test_VUS).to_numpy(float); gen=np.random.default_rng(2024+k); bs=np.array([np.mean(delta[gen.integers(0,len(delta),len(delta))]) for _ in range(10000)]); fold_delta=z.assign(delta=delta).groupby('fold').delta.mean().tolist(); boot.append({'K':k,'delta_mean':float(delta.mean()),'ci_low':float(np.percentile(bs,2.5)),'ci_high':float(np.percentile(bs,97.5)),'prob_delta_gt_0':float(np.mean(bs>0)),'n_outer_test_series':len(delta),'per_fold_delta':json.dumps(fold_delta)})
 pd.DataFrame(boot).to_csv(out/'STAGE3_ENSEMBLE_BOOTSTRAP.csv',index=False)
 s=['# Stage 3-A Ensemble Selection Report','', 'All computations are offline from the nine audited detector score caches. Equal-weight rank averaging is used for every method; no detector or cache was changed.','', '## Results','', rr.groupby(['method','K']).test_macro_VUS.agg(['mean','std']).to_markdown(), '', '## CDU minus Raw paired bootstrap','', pd.DataFrame(boot).to_markdown(index=False), '', '## Decision','', 'The preregistered decision (STRONG/WEAK PASS or FAIL) must be based on K=2/3/4 deltas, confidence intervals, fold consistency, and comparison with random/oracle outputs. Oracle rows are test-label upper bounds and are not deployable.']
 (out/'STAGE3_ENSEMBLE_REPORT.md').write_text('\n'.join(s)+'\n',encoding='utf-8')
 print(pd.DataFrame(boot).to_string(index=False))
if __name__=='__main__': main()
