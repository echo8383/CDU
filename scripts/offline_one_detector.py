"""Compute offline VUS/Hard-VUS/CDU for exactly one cached detector."""
from pathlib import Path
import argparse, os, sys, numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from vus_eval.basic_metrics import generate_curve
from r0_official_compat import find_length_rank_official_compat
from layer2_pilot import oof_cdu
L2=ROOT/'layer2_results'; DATA=ROOT/'Datasets'/'TSB-AD-U'; REF=pd.read_csv(ROOT/'uni_vuspr.csv'); FILES=REF.file.tolist()
GROUPS=pd.read_csv(ROOT/'data'/'trivial_difficulty_groups.csv'); FAMILY=pd.read_csv(ROOT/'data'/'trivial_difficulty_family_balanced.csv')
DETECTORS={'POLY':L2/'poly_pinned_scores','SubPCA':L2/'detector_scores'/'SubPCA','AnomalyTransformer':L2/'detector_scores'/'AnomalyTransformer','TimesNet':L2/'detector_scores'/'TimesNet','MOMENT_ZS':L2/'detector_scores'/'MOMENT_ZS','FITS':L2/'detector_scores'/'FITS','M2N2':L2/'detector_scores'/'M2N2','TranAD':L2/'detector_scores'/'TranAD'}
def load_label(f): return pd.read_csv(DATA/f).dropna()['Label'].to_numpy(int)
def score_path(det,f): return DETECTORS[det]/(f+'.npy')
def vus(s,y):
    w=find_length_rank_official_compat(s,rank=1); s=np.asarray(s,float)
    if not np.isfinite(s).all() or np.ptp(s)==0:return 0.,w
    *_,_,ap=generate_curve(y,s,w,'opt',250); return float(ap),int(w)
def vus_one(args):
    det,f=args; y=load_label(f); s=np.load(score_path(det,f),allow_pickle=False).ravel(); v,w=vus(s,y)
    return {'detector':det,'series_id':f,'dataset_family':f.split('_')[1],'length':len(y),'window':w,'VUS_PR':v,'finite_ratio':float(np.isfinite(s).mean())}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--detector',required=True,choices=list(DETECTORS)); a=ap.parse_args()
    det=a.detector; out=L2/f'{det}_per_series_vus.csv'; rows=[]
    if out.exists(): rows=pd.read_csv(out).to_dict('records')
    done={r['series_id'] for r in rows}; todo=[f for f in FILES if f not in done]
    # Sequential VUS is intentionally used for predictable memory on very long series.
    with ProcessPoolExecutor(max_workers=min(8,max(1,(os.cpu_count() or 2)//2))) as pool:
      futs={pool.submit(vus_one,(det,f)):f for f in todo}
      for j,fu in enumerate(as_completed(futs),1):
        rows.append(fu.result())
        if j%10==0 or j==len(todo): pd.DataFrame(rows).to_csv(out,index=False); print(f'[{det}] VUS {len(done)+j}/{len(FILES)}',flush=True)
    rows=pd.DataFrame(rows).drop_duplicates('series_id').set_index('series_id').reindex(FILES).reset_index(); rows.to_csv(out,index=False)
    g=GROUPS[['series_id','hard20','hard30','hard50','easy20']]; x=rows.merge(g,on='series_id',how='left').merge(FAMILY[['series_id','family_hard20','family_hard30']],on='series_id',how='left')
    specs={'Global_Hard20':x.hard20,'Global_Hard30':x.hard30,'Global_Hard50':x.hard50,'Family_Hard20':x.family_hard20,'Family_Hard30':x.family_hard30,'Easy20':x.easy20,'Full':np.ones(len(x),bool)}
    hv=[]
    for n,m in specs.items():
        m=np.asarray(m,bool); hv.append({'detector':det,'subset':n,'n_series':int(m.sum()),'VUS_PR_macro':float(x.loc[m,'VUS_PR'].mean())})
    pd.DataFrame(hv).to_csv(L2/f'{det}_hard_vus.csv',index=False)
    curves={f:np.load(score_path(det,f),allow_pickle=False).ravel() for f in FILES}
    allr=[]
    for k in (5,10):
        r=oof_cdu(FILES,curves,n_splits=k,C=.1,seed=0)
        p=r['series'].copy(); p['detector']=det; p['folds']=k; allr.append(p); print(f'[{det}] CDU {k}-fold={p.CDU_bits.mean():.9f}',flush=True)
    per=pd.concat(allr,ignore_index=True); per.to_csv(L2/f'{det}_cdu_per_series.csv',index=False)
    p5=allr[0].CDU_bits.to_numpy(float); p10=allr[1].CDU_bits.to_numpy(float); rng=np.random.default_rng(2024); boots=np.array([p5[rng.integers(0,len(p5),len(p5))].mean() for _ in range(10000)])
    summary={'Detector':det,'Raw_VUS':float(rows.VUS_PR.mean()),'CDU_5fold_bits':float(p5.mean()),'CDU_10fold_bits':float(p10.mean()),'CDU_CI_low':float(np.percentile(boots,2.5)),'CDU_CI_high':float(np.percentile(boots,97.5)),'P_CDU_gt_0':float(np.mean(p5>0))}
    for z in hv: summary[z['subset']+'_VUS']=z['VUS_PR_macro']
    sp=L2/'detector_cdu_hardvus_summary_completed.csv'; old=pd.read_csv(sp) if sp.exists() else pd.DataFrame(); old=old[old.Detector!=det] if len(old) and 'Detector' in old else old; pd.concat([old,pd.DataFrame([summary])],ignore_index=True).to_csv(sp,index=False)
    print(summary)
if __name__=='__main__': main()
