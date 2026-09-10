"""Prepare leakage-safe trivial-basis difficulty data only."""
from pathlib import Path
import hashlib, json, subprocess
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT=Path(__file__).resolve().parent; DATA=ROOT/'Datasets'/'TSB-AD-U'; BASIS=ROOT/'layer2_results'/'basis_scores'; OUT=ROOT/'data'
OUT.mkdir(exist_ok=True)
TARGET=['SKAB','SMD','PSM','MSL','SMAP']

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def fam(f): return str(f).split('_')[1]
def cf(v,k):
    files=v.index.tolist(); blocks=np.array_split(np.arange(len(files)),k); rows=[]
    for fold,test in enumerate(blocks):
        train=np.concatenate([b for j,b in enumerate(blocks) if j!=fold])
        selected=v.iloc[train].mean().idxmax()
        rows += [dict(series_id=files[i],dataset_family=fam(files[i]),outer_fold=fold,selected_basis_from_training_fold=selected,heldout_basis_VUS=float(v.iloc[i][selected])) for i in test]
    return pd.DataFrame(rows).sort_values('series_id').reset_index(drop=True)
def load_basis(f):
    z=np.load(BASIS/(f+'.npz'),allow_pickle=False); b=z['basis']; b=b.T if b.shape[0]==31 and b.shape[1]!=31 else b
    return b.astype(float),[str(x) for x in z['names']],z['label'].astype(int)
def get_events(y):
    a=np.flatnonzero(y==1)
    if not len(a): return []
    s=np.r_[0,np.flatnonzero(np.diff(a)>1)+1]; e=np.r_[s[1:]-1,len(a)-1]
    return [(int(a[i]),int(a[j])) for i,j in zip(s,e)]
def main():
    ref=pd.read_csv(ROOT/'uni_vuspr.csv'); files=ref.file.tolist()
    raw=pd.read_csv(ROOT/'step2_oneliner_vuspr.csv').set_index('file').reindex(files)
    drop={'ts_len','anomaly_len','num_anomaly','avg_anomaly_len','anomaly_ratio','point_anomaly','seq_anomaly'}
    cols=[c for c in raw.columns if c not in drop]
    if len(files)!=350 or len(cols)!=31 or raw[cols].isna().any().any(): raise RuntimeError('cached 31-basis VUS artifact invalid')
    v=raw[cols]; h={f:sha(DATA/f) for f in files}
    d5,d10=cf(v,5),cf(v,10)
    for d,name in ((d5,'trivial_difficulty_5fold.csv'),(d10,'trivial_difficulty_10fold.csv')):
        d['dataset_sha256']=d.series_id.map(h); d.to_csv(OUT/name,index=False)
    m=d5.merge(d10[['series_id','heldout_basis_VUS']],on='series_id',suffixes=('_5','_10'))
    rho,_=spearmanr(m.heldout_basis_VUS_5,m.heldout_basis_VUS_10); ad=np.abs(m.heldout_basis_VUS_5-m.heldout_basis_VUS_10)
    n=len(d5); rank=d5.heldout_basis_VUS.rank(method='first'); g=d5.copy(); g['trivial_solvability']=g.heldout_basis_VUS
    g['hard20']=rank<=np.ceil(.2*n); g['hard30']=rank<=np.ceil(.3*n); g['hard50']=rank<=np.ceil(.5*n); g['easy20']=rank>n-np.ceil(.2*n); g['quintile']=np.minimum(5,((rank-1)//np.ceil(n/5)+1).astype(int))
    g.to_csv(OUT/'trivial_difficulty_groups.csv',index=False)
    # Membership stability is supplementary: bins are always defined from the
    # 5-fold scores above, but this quantifies the alternate 10-fold partition.
    rank10=d10.heldout_basis_VUS.rank(method='first'); stab=[]
    for q,name in ((.2,'Hard-20'),(.3,'Hard-30'),(.5,'Hard-50')):
        a=set(g.loc[rank<=np.ceil(q*n),'series_id']); b=set(d10.loc[rank10<=np.ceil(q*n),'series_id']); inter=len(a&b); stab.append((name,inter,len(a|b),inter/len(a|b)))
    cr=[]
    for label,mask in [('All',np.ones(n,bool)),('Hard-20',g.hard20),('Hard-30',g.hard30),('Hard-50',g.hard50),('Easy-20',g.easy20)]:
        sub=g[mask]
        for fa in sorted(set(sub.dataset_family)|set(TARGET)): cr.append({'group':label,'dataset_family':fa,'count':int((sub.dataset_family==fa).sum()),'proportion':float((sub.dataset_family==fa).mean()),'group_size':len(sub)})
    comp=pd.DataFrame(cr); comp.to_csv(OUT/'trivial_difficulty_family_composition.csv',index=False)
    fb=g[['series_id','dataset_family','trivial_solvability']].copy(); fb['family_rank']=fb.groupby('dataset_family').trivial_solvability.rank(method='first'); fb['family_n']=fb.groupby('dataset_family').series_id.transform('size'); fb['family_hard20']=fb.family_rank<=np.ceil(.2*fb.family_n); fb['family_hard30']=fb.family_rank<=np.ceil(.3*fb.family_n)
    fb.to_csv(OUT/'trivial_difficulty_family_balanced.csv',index=False)
    er=[]
    for f in files:
        b,names,y=load_basis(f)
        if len(b)!=len(y): raise RuntimeError('basis cache alignment '+f)
        for eid,(s,e) in enumerate(get_events(y),1):
            r={'series_id':f,'dataset_family':fam(f),'dataset_sha256':h[f],'event_id':eid,'anomaly_start':s,'anomaly_end':e,'anomaly_length':e-s+1}
            for j,nm in enumerate(names): r[nm+'__event_max']=float(b[s:e+1,j].max()); r[nm+'__event_mean']=float(b[s:e+1,j].mean())
            er.append(r)
    ev=pd.DataFrame(er); ev.to_parquet(OUT/'anomaly_event_basis_metadata.parquet',index=False)
    try: commit=subprocess.check_output(['git','-C',r'D:\CSIES\AI4Energy\others\TSB-AD','rev-parse','HEAD'],text=True).strip()
    except Exception: commit='unavailable'
    prov={'dataset_files':350,'dataset_sha256_manifest':hashlib.sha256('\n'.join(f+','+h[f] for f in files).encode()).hexdigest(),'basis_vus_source':'step2_oneliner_vuspr.csv','basis_metric':'generate_curve(..., slidingWindow=100, opt, thre=250)[7]','basis_pointwise_source':'layer2_results/basis_scores/*.npz rank-normalized basis curves','basis_definitions':cols,'window_logic':'fixed 100 from cached VUS artifact','tsbad_commit':commit,'fold_assignment':'deterministic np.array_split in uni_vuspr.csv order'}
    audit=['# Trivial-Hard Data Audit','',f'- Unique series: {g.series_id.nunique()}; 5-fold rows: {len(d5)}; 10-fold rows: {len(d10)}.',f'- 31 basis scorers, finite VUS: {bool(np.isfinite(v.to_numpy(float)).all())}.', '- Leakage safety: each outer fold selects one scorer from training-series mean VUS only; no held-out series enters its own selection.', '- No detector score, detector training, CDU output, or per-series best-of-31 oracle is imported or used.',f'- Point-wise cache alignment: PASS for all 350 series; event rows: {len(ev)}.','', '## Provenance','', '```json',json.dumps(prov,ensure_ascii=False,indent=2),'```']
    (ROOT/'TRIVIAL_HARD_DATA_AUDIT.md').write_text('\n'.join(audit),encoding='utf-8')
    hh=comp[comp.group=='Hard-20'].sort_values('proportion',ascending=False).iloc[0]
    report=['# Natural Trivial-Hard Evaluation Data','',f'- Series: {n}.',f'- 5-fold trivial solvability: mean={g.trivial_solvability.mean():.6f}; median={g.trivial_solvability.median():.6f}; SD={g.trivial_solvability.std():.6f}; min={g.trivial_solvability.min():.6f}; max={g.trivial_solvability.max():.6f}.',f'- 5 vs 10 fold: Spearman rho={rho:.6f}; mean absolute difference={ad.mean():.6f}; median absolute difference={ad.median():.6f}.', '- 5/10 hard-set Jaccard: '+', '.join(f'{x[0]}={x[3]:.3f}' for x in stab)+'.',f'- Global subsets: Hard-20={g.hard20.sum()}; Hard-30={g.hard30.sum()}; Hard-50={g.hard50.sum()}; Easy-20={g.easy20.sum()}.',f'- Family-balanced: Family-Hard-20={fb.family_hard20.sum()}; Family-Hard-30={fb.family_hard30.sum()}.',f'- Largest Hard-20 family: {hh.dataset_family} ({hh["count"]}/{hh.group_size}; {hh.proportion:.1%}).','- Missing data/anomalies: none. No detector evaluation was performed.']
    (ROOT/'TRIVIAL_HARD_DATA_REPORT.md').write_text('\n'.join(report),encoding='utf-8')
    print('\n'.join(report))
if __name__=='__main__': main()
