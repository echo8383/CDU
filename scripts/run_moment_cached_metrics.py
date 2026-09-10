"""Offline Raw-VUS/Hard-VUS/CDU for cached MOMENT scores.

No detector inference is performed.  The script consumes the already complete
MOMENT_ZS and MOMENT_FT point-score caches and writes one detector at a time to
keep memory bounded and make interruption/resume possible.
"""
from pathlib import Path
import argparse, hashlib, json, sys
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[1]; L2 = ROOT/'layer2_results'; DATA = ROOT/'Datasets'/'TSB-AD-U'
sys.path.insert(0, str(ROOT)); sys.path.insert(0, r'D:\CSIES\AI4Energy\others\TSB-AD')
from vus_eval.basic_metrics import generate_curve
from r0_official_compat import find_length_rank_official_compat

FILES = pd.read_csv(ROOT/'uni_vuspr.csv').file.astype(str).tolist()
DIRS = {d: L2/'detector_scores'/d for d in ('MOMENT_ZS','MOMENT_FT')}
GROUPS = pd.read_csv(ROOT/'data'/'trivial_difficulty_groups.csv')
FAMILY = pd.read_csv(ROOT/'data'/'trivial_difficulty_family_balanced.csv')

def load_data(f):
    d = pd.read_csv(DATA/f).dropna(); return d.iloc[:,:-1].to_numpy(float), d.Label.to_numpy(int)
def raw_window(f):
    x,_ = load_data(f); return int(find_length_rank_official_compat(x[:,0].reshape(-1,1), rank=1))
def score(det,f): return np.load(DIRS[det]/(f+'.npy'), allow_pickle=False).ravel()
def rank01(x):
    x=np.asarray(x,float); return (np.argsort(np.argsort(x,kind='mergesort'),kind='mergesort')+.5)/len(x)
def vus(y,s,w):
    if not np.isfinite(s).all() or np.ptp(s)==0: return 0.0
    return float(generate_curve(y,s,w,'opt',250)[7])
def compute_vus(det):
    out=L2/f'{det}_audited_per_series_vus.csv'; old=pd.read_csv(out) if out.exists() else pd.DataFrame(); done=set(old.series_id.astype(str)) if len(old) else set(); rows=old.to_dict('records') if len(old) else []
    for i,f in enumerate(FILES,1):
        if f in done: continue
        _,y=load_data(f); s=score(det,f); w=raw_window(f); rows.append({'detector':det,'series_id':f,'dataset_family':f.split('_')[1],'length':len(y),'window':w,'VUS_PR':vus(y,s,w),'finite_ratio':float(np.isfinite(s).mean()),'score_hash':hashlib.sha256(np.asarray(s,dtype=np.float64).tobytes()).hexdigest()})
        if i%10==0 or i==len(FILES): pd.DataFrame(rows).drop_duplicates('series_id').set_index('series_id').reindex(FILES).reset_index().to_csv(out,index=False); print(f'[{det}] VUS {i}/350',flush=True)
    d=pd.DataFrame(rows).drop_duplicates('series_id').set_index('series_id').reindex(FILES).reset_index(); d.to_csv(out,index=False); return d
def cdu(det,k):
    data=[]
    for f in FILES:
        z=np.load(L2/'basis_scores'/(f+'.npz'),allow_pickle=False); B=z['basis']; B=B.T if B.shape[0]==31 and B.shape[1]!=31 else B; y=z['label'].astype(int); s=rank01(score(det,f)); data.append((B.astype(float),y,s))
    blocks=np.array_split(np.arange(len(FILES)),k); rows=[]
    for fold,test in enumerate(blocks):
        tr=np.concatenate([b for j,b in enumerate(blocks) if j!=fold]); X0=np.vstack([data[i][0] for i in tr]); X1=np.vstack([np.column_stack([data[i][0],data[i][2]]) for i in tr]); Y=np.concatenate([data[i][1] for i in tr])
        kw=dict(C=.1,penalty='l2',solver='liblinear',class_weight='balanced',max_iter=300,random_state=0); m0=LogisticRegression(**kw).fit(X0,Y); m1=LogisticRegression(**kw).fit(X1,Y)
        for i in test:
            B,y,s=data[i]; p0=np.clip(m0.predict_proba(B)[:,1],1e-7,1-1e-7); p1=np.clip(m1.predict_proba(np.column_stack([B,s]))[:,1],1e-7,1-1e-7); l0=-(y*np.log2(p0)+(1-y)*np.log2(1-p0)); l1=-(y*np.log2(p1)+(1-y)*np.log2(1-p1)); rows.append({'detector':det,'series_id':FILES[i],'folds':k,'fold':fold,'L0_bits':l0.mean(),'L1_bits':l1.mean(),'CDU_bits':(l0-l1).mean(),'NCDU':(l0-l1).mean()/max(l0.mean(),1e-12),'n_points':len(y)})
        print(f'[{det}] CDU {k}-fold fold {fold+1}/{k}',flush=True)
    return pd.DataFrame(rows)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--detector',choices=['MOMENT_ZS','MOMENT_FT','both'],default='both'); a=ap.parse_args(); ds=['MOMENT_ZS','MOMENT_FT'] if a.detector=='both' else [a.detector]
    allsum=[]
    for det in ds:
        manifest=L2/f'{det}_score_manifest.csv'; n=len(pd.read_csv(manifest)) if manifest.exists() else 0
        if n!=350: raise RuntimeError(f'{det} manifest has {n}, expected 350')
        v=compute_vus(det); g=GROUPS[['series_id','hard20','hard30','hard50','easy20']]; f=FAMILY[['series_id','family_hard20','family_hard30']]; x=v.merge(g,on='series_id').merge(f,on='series_id')
        specs={'Global_Hard20':x.hard20,'Global_Hard30':x.hard30,'Global_Hard50':x.hard50,'Family_Hard20':x.family_hard20,'Family_Hard30':x.family_hard30,'Easy20':x.easy20,'Full':np.ones(len(x),bool)}
        hv=pd.DataFrame([{'detector':det,'subset':n,'n_series':int(np.asarray(m,bool).sum()),'VUS_PR_macro':float(x.loc[np.asarray(m,bool),'VUS_PR'].mean())} for n,m in specs.items()]); hv.to_csv(L2/f'{det}_audited_hard_vus.csv',index=False)
        rs=[]
        for k in (5,10): rs.append(cdu(det,k))
        per=pd.concat(rs,ignore_index=True); per.to_csv(L2/f'{det}_audited_cdu_per_series.csv',index=False)
        p5=rs[0].CDU_bits.to_numpy(float); p10=rs[1].CDU_bits.to_numpy(float); rng=np.random.default_rng(2024); b=np.array([p5[rng.integers(0,len(p5),len(p5))].mean() for _ in range(10000)])
        allsum.append({'Detector':det,'Raw_VUS':v.VUS_PR.mean(),'CDU_5fold_bits':p5.mean(),'CDU_10fold_bits':p10.mean(),'CDU_CI_low':np.percentile(b,2.5),'CDU_CI_high':np.percentile(b,97.5),'positive_series_ratio':(p5>0).mean(),'bootstrap_prob_macro_positive':(b>0).mean(),'Family_Hard20_VUS':hv.loc[hv.subset=='Family_Hard20','VUS_PR_macro'].iloc[0],'Family_Hard30_VUS':hv.loc[hv.subset=='Family_Hard30','VUS_PR_macro'].iloc[0],'status':'CACHE_OFFLINE_COMPLETE'})
        print(json.dumps(allsum[-1],indent=2),flush=True)
    pd.DataFrame(allsum).to_csv(L2/'moment_audited_summary.csv',index=False)
if __name__=='__main__': main()
