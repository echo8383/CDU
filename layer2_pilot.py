"""Layer 2 CDU pilot: point-wise basis cache and leakage-safe OOF probes.

当前阶段只验证估计器，不抓取真实 detector 曲线，也不生成 detector 排名。
"""
from pathlib import Path
import gc
import json
import time
import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
import oneliners as ol

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'Datasets' / 'TSB-AD-U'
L2 = ROOT / 'layer2_results'
BASIS_DIR = L2 / 'basis_scores'
BASIS_DIR.mkdir(parents=True, exist_ok=True)

def rank01(x):
    x = np.asarray(x, float)
    order = np.argsort(np.argsort(x, kind='mergesort'), kind='mergesort')
    return (order + .5) / len(x)

def load_series(file):
    d = pd.read_csv(DATA / file).dropna()
    x = d.iloc[:, 0].to_numpy(float); y = d['Label'].to_numpy(int)
    sd = x.std(); x = (x - x.mean()) / (sd if sd > 0 else 1.)
    return x, y

def cache_basis(file, force=False):
    out = BASIS_DIR / (str(file) + '.npz')
    if out.exists() and not force:
        z = np.load(out, allow_pickle=False)
        B = z['basis']
        # 旧缓存曾保存为 (31,T)；probe 统一使用 (T,31)。
        if B.ndim == 2 and B.shape[0] == 31 and B.shape[1] != 31:
            B = B.T
        return B, z['label'], [str(x) for x in z['names']]
    x, y = load_series(file)
    names, curves = ol.build_basis(x)
    B = np.column_stack([rank01(v) for v in curves]).astype('float32')
    np.savez_compressed(out, basis=B, label=y.astype('int8'), names=np.asarray(names))
    return B, y, names

def cache_all(limit=None):
    ref = pd.read_csv(ROOT / 'uni_vuspr.csv')
    files = ref.file.tolist()[:limit] if limit else ref.file.tolist()
    t0 = time.time(); done = 0
    for i, f in enumerate(files, 1):
        cache_basis(f); done += 1
        if i % 10 == 0 or i == len(files):
            print(f'basis curves {i}/{len(files)}  elapsed={time.time()-t0:.1f}s', flush=True)
    return files

def oof_cdu(files, detector_curves, n_splits=5, C=.1, seed=0):
    """whole-series OOF logistic; 每条 series 等权，返回 bits 与 NCDU。"""
    n = len(files); blocks = np.array_split(np.arange(n), n_splits)
    cdu0=[]; cdu1=[]; series_rows=[]; detail=[]
    # Load one series at a time inside each fold.  Keeping all 31-feature
    # matrices resident makes the 350-series run unnecessarily memory-heavy;
    # this streaming form is numerically identical and preserves the exact
    # point-wise estimator.
    lengths=[]
    for f in files:
        B,y,_=cache_basis(f); s=np.asarray(detector_curves[f],float)
        if len(s)!=len(y): raise ValueError(f'curve length mismatch: {f}')
        lengths.append(len(y))
    for k, test_ids in enumerate(blocks):
        train_ids = np.concatenate([b for j,b in enumerate(blocks) if j != k])
        total_train = int(sum(lengths[i] for i in train_ids))
        X0=np.empty((total_train,31),dtype=np.float64); Y=np.empty(total_train,dtype=np.int8)
        pos=0
        for i in train_ids:
            B,y,_=cache_basis(files[i]); n=len(y); X0[pos:pos+n]=B; Y[pos:pos+n]=y; pos+=n
        # Keep the estimator and all hyperparameters unchanged, but fit the
        # two nested models sequentially so X0 and X1 are not resident at the
        # same time (the full 350-series point matrix is several GB).
        X0=np.vstack(X0)
        m0=LogisticRegression(C=C, penalty='l2', solver='liblinear', class_weight='balanced', max_iter=300, random_state=seed)
        m0.fit(X0,Y)
        del X0; gc.collect()
        # Construct M1 features only after X0 has been released.
        X1=np.empty((total_train,32),dtype=np.float64); pos=0
        for i in train_ids:
            B,y,_=cache_basis(files[i]); n=len(y); X1[pos:pos+n,:31]=B; X1[pos:pos+n,31]=rank01(np.asarray(detector_curves[files[i]],float)); pos+=n
        m1=LogisticRegression(C=C, penalty='l2', solver='liblinear', class_weight='balanced', max_iter=300, random_state=seed)
        m1.fit(X1,Y)
        del X1, Y; gc.collect()
        for i in test_ids:
            B,y,_=cache_basis(files[i]); s=rank01(np.asarray(detector_curves[files[i]],float)); p0=m0.predict_proba(B)[:,1]; p1=m1.predict_proba(np.column_stack([B,s]))[:,1]
            l0=-(y*np.log2(np.clip(p0,1e-7,1-1e-7))+(1-y)*np.log2(np.clip(1-p0,1e-7,1-1e-7)))
            l1=-(y*np.log2(np.clip(p1,1e-7,1-1e-7))+(1-y)*np.log2(np.clip(1-p1,1e-7,1-1e-7)))
            gap=l0-l1; cdu0.append(float(l0.mean())); cdu1.append(float(l1.mean()))
            # Use the held-out series corresponding to index ``i``.  The
            # previous code reused the outer loading-loop variable ``f``
            # (the last filename), corrupting IDs in per-series output while
            # leaving aggregate loss values numerically intact.
            row={'series_id':files[i],'fold':k,'L0_bits':float(l0.mean()),'L1_bits':float(l1.mean()),'CDU_bits':float(gap.mean()),'NCDU':float(gap.mean()/max(l0.mean(),1e-12))}
            series_rows.append(row); detail.extend({'series_id':f,'time':t,'y':int(yy),'loss0':float(a),'loss1':float(b),'delta_bits':float(dd)} for t,(yy,a,b,dd) in enumerate(zip(y,l0,l1,gap)))
    R=pd.DataFrame(series_rows); D=pd.DataFrame(detail)
    return {'L0_bits':float(np.mean(cdu0)), 'L1_bits':float(np.mean(cdu1)), 'CDU_bits':float(R.CDU_bits.mean()), 'NCDU':float(R.NCDU.mean()), 'series':R, 'detail':D}

def controls(files):
    """四个不可作弊控制：copy、单调 copy、random、added signal。"""
    rng=np.random.default_rng(0); out=[]
    var_curves={}; labels={}
    for f in files:
        B,y,names=cache_basis(f); j=names.index('Var-96'); var_curves[f]=B[:, j]; labels[f]=y
    for name, maker in [
        ('Var96_self', lambda f: var_curves[f]),
        ('Var96_monotonic', lambda f: 100*var_curves[f]+7),
        ('Random', lambda f: rng.random(len(var_curves[f]))),
    ]:
        r=oof_cdu(files,{f:maker(f) for f in files}); out.append({'control':name,**{k:r[k] for k in ['L0_bits','L1_bits','CDU_bits','NCDU']}})
    for lam in [0,.1,.25,.5,1.0]:
        curves={f:var_curves[f]+lam*labels[f] for f in files}
        r=oof_cdu(files,curves); out.append({'control':f'AddedSignal_{lam:g}',**{k:r[k] for k in ['L0_bits','L1_bits','CDU_bits','NCDU']}})
    return pd.DataFrame(out)

def true_cmi_mc(seed=0, n=1000000, lam=0.0, alpha=(.4,-.3,0,0,0), chunk=100000):
    """由生成模型直接积分 I(Y;Z|B)，不依赖 probe。"""
    rng=np.random.default_rng(seed); a=np.asarray(alpha,float); h0=[]; h1=[]; done=0
    while done < n:
        m=min(chunk,n-done); B=rng.normal(size=(m,5)); Z=rng.normal(size=m)
        eta=B@a; p1=expit(eta+lam*Z)
        # E_Z sigma(eta+lambda Z) 用同一大样本的 conditional Monte Carlo 近似。
        p0=np.mean(expit(eta[:,None]+lam*rng.normal(size=(m,16))),axis=1)
        def h(p): return -(p*np.log2(np.clip(p,1e-15,1))+(1-p)*np.log2(np.clip(1-p,1e-15,1)))
        h0.extend(h(p0).tolist()); h1.extend(h(p1).tolist())
        done += m
    return float(np.mean(h0)-np.mean(h1))

def synthetic(seed=0, n_series=100, T=300, lam=0.0):
    rng=np.random.default_rng(seed); B=rng.normal(size=(n_series*T,5)); z=rng.normal(size=n_series*T)
    y=rng.binomial(1,expit(.4*B[:,0]-.3*B[:,1]+lam*z))
    folds=np.array_split(np.arange(n_series),5); l0=[]; l1=[]
    for test in folds:
        train=np.concatenate([np.arange(a*T,(a+1)*T) for a in range(n_series) if a not in test])
        ev=np.concatenate([np.arange(a*T,(a+1)*T) for a in test])
        m0=LogisticRegression(C=.1,class_weight='balanced',solver='liblinear').fit(B[train],y[train])
        m1=LogisticRegression(C=.1,class_weight='balanced',solver='liblinear').fit(np.column_stack([B[train],z[train]]),y[train])
        l0.append(log_loss(y[ev],m0.predict_proba(B[ev])[:,1],labels=[0,1])/np.log(2))
        Xev = np.column_stack([B[ev], z[ev]])
        l1.append(log_loss(y[ev],m1.predict_proba(Xev)[:,1],labels=[0,1])/np.log(2))
    return float(np.mean(l0)-np.mean(l1))

def main():
    files=cache_all(); pd.DataFrame(controls(files[:min(20,len(files))])).to_csv(L2/'control_results.csv',index=False)
    syn=[]
    for lam in [0,.001,.0025,.005,.01,.025,.05,.1,.25,.5,1.0]:
        vals=[synthetic(seed=s,lam=lam) for s in range(3)]
        syn.append({'lambda':lam,'true_cmi_bits':true_cmi_mc(seed=100,lam=lam,n=200000),'CDU_mean':float(np.mean(vals)),'CDU_sd':float(np.std(vals,ddof=1))})
    pd.DataFrame(syn).to_csv(L2/'synthetic_cmi.csv',index=False)
    c=pd.read_csv(L2/'control_results.csv'); s=pd.read_csv(L2/'synthetic_cmi.csv')
    checks={'basis_files':len(list(BASIS_DIR.glob('*.npz'))),'control':c.to_dict('records'),'synthetic':s.to_dict('records'),
            'random_abs_cdu':float(abs(c.loc[c.control=='Random','CDU_bits'].iloc[0])),
            'copy_abs_cdu':float(abs(c.loc[c.control=='Var96_self','CDU_bits'].iloc[0])),
            'added_monotonic':bool(np.all(np.diff(s.CDU_mean.to_numpy())>=-0.01))}
    (L2/'pilot_sanity.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(checks,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
