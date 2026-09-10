from pathlib import Path
import argparse, json, numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
ROOT=Path(__file__).resolve().parents[1]; L2=ROOT/'layer2_results'; DATA=ROOT/'Datasets'/'TSB-AD-U'; sys_path=str(ROOT)
import sys; sys.path.insert(0,sys_path)
REF=pd.read_csv(ROOT/'uni_vuspr.csv'); FILES=REF.file.tolist()
DIRS={'POLY':L2/'poly_pinned_scores','SubPCA':L2/'detector_scores'/'SubPCA','AnomalyTransformer':L2/'detector_scores'/'AnomalyTransformer','TimesNet':L2/'detector_scores'/'TimesNet','MOMENT_ZS':L2/'detector_scores'/'MOMENT_ZS'}
def rank01(x):
 x=np.asarray(x,float); return (np.argsort(np.argsort(x,kind='mergesort'),kind='mergesort')+.5)/len(x)
def load(det,f):
 z=np.load(L2/'basis_scores'/(f+'.npz')); B=z['basis']; B=B.T if B.shape[0]==31 and B.shape[1]!=31 else B; y=z['label'].astype(int); s=np.load(DIRS[det]/(f+'.npy')).ravel(); return B.astype(float),y,rank01(s)
def run(det,k):
 data=[load(det,f) for f in FILES]; blocks=np.array_split(np.arange(len(FILES)),k); rows=[]
 for fold,test in enumerate(blocks):
  train=np.concatenate([b for j,b in enumerate(blocks) if j!=fold]); X0=np.vstack([data[i][0] for i in train]); X1=np.vstack([np.column_stack([data[i][0],data[i][2]]) for i in train]); Y=np.concatenate([data[i][1] for i in train]);
  m0=LogisticRegression(C=.1,solver='liblinear',class_weight='balanced',max_iter=300,random_state=0).fit(X0,Y); m1=LogisticRegression(C=.1,solver='liblinear',class_weight='balanced',max_iter=300,random_state=0).fit(X1,Y)
  print(f'[{det}] fold {fold+1}/{k}',flush=True)
  for i in test:
   B,y,s=data[i]; p0=np.clip(m0.predict_proba(B)[:,1],1e-7,1-1e-7); p1=np.clip(m1.predict_proba(np.column_stack([B,s]))[:,1],1e-7,1-1e-7); l0=-(y*np.log2(p0)+(1-y)*np.log2(1-p0)); l1=-(y*np.log2(p1)+(1-y)*np.log2(1-p1)); rows.append({'detector':det,'folds':k,'fold':fold,'series_id':FILES[i],'L0_bits':l0.mean(),'L1_bits':l1.mean(),'CDU_bits':(l0-l1).mean(),'NCDU':(l0-l1).mean()/max(l0.mean(),1e-12),'n_points':len(y)})
 return pd.DataFrame(rows)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--detector',required=True,choices=DIRS); a=ap.parse_args(); out=L2/f'{a.detector}_cdu_per_series.csv'; r5=run(a.detector,5); r10=run(a.detector,10); pd.concat([r5,r10],ignore_index=True).to_csv(out,index=False); x=L2/f'{a.detector}_per_series_vus.csv'; raw=pd.read_csv(x).VUS_PR.mean(); p=r5.CDU_bits.to_numpy(); q=r10.CDU_bits.to_numpy(); rng=np.random.default_rng(2024); b=np.array([p[rng.integers(0,len(p),len(p))].mean() for _ in range(10000)]); s={'Detector':a.detector,'Raw_VUS':raw,'CDU_5fold_bits':p.mean(),'CDU_10fold_bits':q.mean(),'CDU_CI_low':np.percentile(b,2.5),'CDU_CI_high':np.percentile(b,97.5),'P_CDU_gt_0':np.mean(p>0)}; sp=L2/'detector_cdu_hardvus_summary_completed.csv'; old=pd.read_csv(sp) if sp.exists() else pd.DataFrame(); old=old[old.Detector!=a.detector] if len(old) and 'Detector' in old else old; pd.concat([old,pd.DataFrame([s])],ignore_index=True).to_csv(sp,index=False); print(json.dumps(s,indent=2))
if __name__=='__main__': main()
