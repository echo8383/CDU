"""Offline metrics from already cached point-wise detector scores.

No detector is executed here.  Reads score caches and existing basis caches,
then computes per-series VUS/Hard-VUS and OOF CDU for completed detectors.
"""
from pathlib import Path
import sys, json, hashlib, os
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vus_eval.basic_metrics import generate_curve
from r0_official_compat import find_length_rank_official_compat
from layer2_pilot import oof_cdu

L2 = ROOT / 'layer2_results'
DATA = ROOT / 'Datasets' / 'TSB-AD-U'
REF = pd.read_csv(ROOT / 'uni_vuspr.csv')
FILES = REF['file'].tolist()
GROUPS = pd.read_csv(ROOT / 'data' / 'trivial_difficulty_groups.csv')
FAMILY = pd.read_csv(ROOT / 'data' / 'trivial_difficulty_family_balanced.csv')

DETECTORS = {
    'POLY': L2 / 'poly_pinned_scores',
    'SubPCA': L2 / 'detector_scores' / 'SubPCA',
    'AnomalyTransformer': L2 / 'detector_scores' / 'AnomalyTransformer',
    'TimesNet': L2 / 'detector_scores' / 'TimesNet',
}

def load_label(f):
    d = pd.read_csv(DATA / f).dropna()
    return d['Label'].to_numpy(int)

def vus(score, label):
    w = find_length_rank_official_compat(score, rank=1)
    score = np.asarray(score, float)
    if not np.isfinite(score).all() or np.ptp(score) == 0:
        return 0.0, w
    *_, _, ap = generate_curve(label, score, w, 'opt', 250)
    return float(ap), int(w)

def score_path(det, f):
    d = DETECTORS[det]
    p = d / (f + '.npy')
    if not p.exists():
        # POLY cache naming is also filename.npy; retain a clear error.
        raise FileNotFoundError(str(p))
    return p

def _vus_one(args):
    det, f = args
    y = load_label(f); s = np.load(score_path(det, f), allow_pickle=False).ravel()
    if len(s) != len(y): raise RuntimeError(f'{det} length mismatch {f}: {len(s)} vs {len(y)}')
    v, w = vus(s, y)
    return {'detector':det, 'series_id':f, 'dataset_family':f.split('_')[1], 'length':len(y),
            'window':w, 'VUS_PR':v, 'finite_ratio':float(np.isfinite(s).mean()),
            'score_hash':hashlib.sha256(np.ascontiguousarray(s,dtype=np.float64).tobytes()).hexdigest()}

def main():
    all_summary = []
    for det, d in DETECTORS.items():
        rows = []
        curves = {}
        outvus=L2/f'{det}_per_series_vus.csv'
        if outvus.exists():
            old=pd.read_csv(outvus); rows=old.to_dict('records')
        done={r['series_id'] for r in rows}; todo=[f for f in FILES if f not in done]
        with ProcessPoolExecutor(max_workers=min(8, max(1,(os.cpu_count() or 2)//2))) as pool:
            futs={pool.submit(_vus_one,(det,f)):f for f in todo}
            for j,fut in enumerate(as_completed(futs),1):
                rows.append(fut.result())
                if j%10==0 or j==len(todo):
                    pd.DataFrame(rows).drop_duplicates('series_id').set_index('series_id').reindex(FILES).reset_index().to_csv(outvus,index=False)
                    print(f'[{det}] VUS {len(done)+j}/{len(FILES)}',flush=True)
        rows=pd.DataFrame(rows).drop_duplicates('series_id').set_index('series_id').reindex(FILES).reset_index().to_dict('records')
        for f in FILES:
            curves[f]=np.load(score_path(det,f),allow_pickle=False).ravel()
        vus_df = pd.DataFrame(rows)
        vus_df.to_csv(outvus, index=False)
        # Hard groups are fixed externally; only aggregate existing IDs.
        g = GROUPS[['series_id','hard20','hard30','hard50','easy20']]
        x = vus_df.merge(g, on='series_id', how='left')
        fb = FAMILY[['series_id','family_hard20','family_hard30']]
        x = x.merge(fb, on='series_id', how='left')
        specs = {'Global_Hard20':x.hard20, 'Global_Hard30':x.hard30,
                 'Global_Hard50':x.hard50, 'Family_Hard20':x.family_hard20,
                 'Family_Hard30':x.family_hard30, 'Easy20':x.easy20,
                 'Full':np.ones(len(x),dtype=bool)}
        hv=[]
        for name, mask in specs.items():
            mask=np.asarray(mask,dtype=bool)
            hv.append({'detector':det,'subset':name,'n_series':int(mask.sum()),
                       'VUS_PR_macro':float(x.loc[mask,'VUS_PR'].mean())})
        pd.DataFrame(hv).to_csv(L2 / f'{det}_hard_vus.csv', index=False)
        print(f'[{det}] Raw VUS={vus_df.VUS_PR.mean():.9f}', flush=True)
        # CDU uses existing cached basis and this detector curve only.
        r5 = oof_cdu(FILES, curves, n_splits=5, C=.1, seed=0)
        r10 = oof_cdu(FILES, curves, n_splits=10, C=.1, seed=0)
        p5 = r5['series'].copy(); p5['detector']=det; p5['folds']=5
        p10 = r10['series'].copy(); p10['detector']=det; p10['folds']=10
        per = pd.concat([p5,p10], ignore_index=True)
        per.to_csv(L2 / f'{det}_cdu_per_series.csv', index=False)
        # Paired series bootstrap on 5-fold deltas.
        vals=p5.CDU_bits.to_numpy(float); rng=np.random.default_rng(2024)
        boots=np.array([vals[rng.integers(0,len(vals),len(vals))].mean() for _ in range(10000)])
        all_summary.append({'Detector':det,'Raw_VUS':vus_df.VUS_PR.mean(),
          'CDU_5fold_bits':vals.mean(),'CDU_10fold_bits':p10.CDU_bits.mean(),
          'CDU_CI_low':np.percentile(boots,2.5),'CDU_CI_high':np.percentile(boots,97.5),
          'P_CDU_gt_0':float(np.mean(vals>0)),
          'Global_Hard20_VUS':hv[0]['VUS_PR_macro'],'Global_Hard30_VUS':hv[1]['VUS_PR_macro'],
          'Global_Hard50_VUS':hv[2]['VUS_PR_macro'],'Family_Hard20_VUS':hv[3]['VUS_PR_macro'],
          'Family_Hard30_VUS':hv[4]['VUS_PR_macro'],'Easy20_VUS':hv[5]['VUS_PR_macro']})
        print(f'[{det}] CDU5={vals.mean():.9f} CDU10={p10.CDU_bits.mean():.9f}', flush=True)
    pd.DataFrame(all_summary).to_csv(L2/'detector_cdu_hardvus_summary_completed.csv', index=False)
    print(pd.DataFrame(all_summary).to_string(index=False))

if __name__ == '__main__': main()
