"""POLY-only Layer-2 CDU using the frozen R0 point-score cache."""
from pathlib import Path
import hashlib, json, time
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression

ROOT=Path(__file__).resolve().parent; L2=ROOT/'layer2_results'; DATA=ROOT/'Datasets'/'TSB-AD-U'
R0=pd.read_csv(L2/'poly_reproducibility_350.csv'); FILES=R0.series_id.tolist(); BASIS=L2/'basis_scores'; SCORES=L2/'poly_pinned_scores'
OUT=L2/'poly_full_cdu_per_series.csv'; CONT=L2/'poly_full_controls.csv'; REPORT=ROOT/'POLY_REPRODUCIBLE_CDU_REPORT.md'

def rank01(x):
    x=np.asarray(x,float); return (np.argsort(np.argsort(x,kind='mergesort'),kind='mergesort')+.5)/len(x)
def load(f):
    z=np.load(BASIS/(f+'.npz'),allow_pickle=False); B=z['basis']; B=B.T if B.shape[0]==31 and B.shape[1]!=31 else B; y=z['label'].astype(int)
    s=np.load(SCORES/(f+'.npy')); assert len(s)==len(y), f
    return B.astype(float), y, rank01(s), rank01(B[:,list(z['names']).index('Var-96')])
def run(condition, curves, k, seed=0):
    rng=np.random.default_rng(seed); data=[load(f) for f in FILES]; blocks=np.array_split(np.arange(len(FILES)),k); rows=[]
    for fold,test in enumerate(blocks):
        train=np.concatenate([b for j,b in enumerate(blocks) if j!=fold]); X0=np.vstack([data[i][0] for i in train]); X1=np.vstack([np.column_stack([data[i][0],curves[i]]) for i in train]); Y=np.concatenate([data[i][1] for i in train])
        m0=LogisticRegression(C=.1,penalty='l2',solver='liblinear',class_weight='balanced',max_iter=300,random_state=seed).fit(X0,Y)
        m1=LogisticRegression(C=.1,penalty='l2',solver='liblinear',class_weight='balanced',max_iter=300,random_state=seed).fit(X1,Y)
        for i in test:
            B,y,_,_=data[i]; s=curves[i]; p0=m0.predict_proba(B)[:,1]; p1=m1.predict_proba(np.column_stack([B,s]))[:,1]; p0=np.clip(p0,1e-7,1-1e-7); p1=np.clip(p1,1e-7,1-1e-7)
            l0=-(y*np.log2(p0)+(1-y)*np.log2(1-p0)); l1=-(y*np.log2(p1)+(1-y)*np.log2(1-p1)); d=l0-l1
            rows.append({'condition':condition,'folds':k,'series_id':FILES[i],'fold':fold,'L0_bits':l0.mean(),'L1_bits':l1.mean(),'CDU_bits':d.mean(),'NCDU':d.mean()/max(l0.mean(),1e-12),'n_points':len(y)})
    return pd.DataFrame(rows)
def main():
    if len(R0)!=350 or not (R0.status=='PASS').all(): raise SystemExit('R0 not 350/350 PASS')
    loaded=[load(f) for f in FILES]; poly=[x[2] for x in loaded]; var=[x[3] for x in loaded]; rng=np.random.default_rng(2024); randoms=[rng.random(len(x[1])) for x in loaded]
    allrows=[]; summaries=[]
    for k in (5,10):
        for name,curves in [('Var96_self',var),('Var96_monotonic',[100*x+7 for x in var]),('Random',randoms),('POLY',poly)]:
            t=time.time(); rr=run(name,curves,k); allrows.append(rr); summaries.append({'condition':name,'folds':k,'L0_bits':rr.L0_bits.mean(),'L1_bits':rr.L1_bits.mean(),'CDU_bits':rr.CDU_bits.mean(),'NCDU':rr.NCDU.mean(),'runtime_sec':time.time()-t})
            print(name,k,rr.CDU_bits.mean(),flush=True)
    D=pd.concat(allrows,ignore_index=True); D.to_csv(OUT,index=False); pd.DataFrame(summaries).to_csv(CONT,index=False)
    p=D[(D.condition=='POLY')&(D.folds==5)].CDU_bits.to_numpy(); rng=np.random.default_rng(7); boots=[]
    for _ in range(10000): boots.append(float(np.mean(p[rng.integers(0,len(p),len(p))])))
    s5=D[(D.condition=='POLY')&(D.folds==5)].CDU_bits; s10=D[(D.condition=='POLY')&(D.folds==10)].CDU_bits
    raw=R0.pinned_vus.astype(float); report=f'''# POLY Reproducible CDU Report

R0 pinned environment: `official_historical`, commit `8b363e350ae047a8115a594d1e9da64aae09b852`, seed 2024. Historical leaderboard VUS is not mixed into this result; raw VUS below is the pinned local VUS.

## POLY result (macro, series-weighted)

- Pinned raw VUS: `{raw.mean():.12g}`
- CDU (5-fold): `{s5.mean():.12g}` bits
- Paired series bootstrap 95% CI: `[{np.percentile(boots,2.5):.12g}, {np.percentile(boots,97.5):.12g}]` bits
- P(CDU > 0): `{np.mean(s5.to_numpy()>0):.6g}`
- CDU (10-fold): `{s10.mean():.12g}` bits
- 5/10-fold difference: `{(s5.mean()-s10.mean()):.12g}` bits

Controls are in `layer2_results/poly_full_controls.csv`; per-series held-out losses and deltas are in `layer2_results/poly_full_cdu_per_series.csv`. Negative finite-sample CDU values are retained and are not clipped.
'''
    REPORT.write_text(report,encoding='utf-8'); print(report)
if __name__=='__main__': main()
