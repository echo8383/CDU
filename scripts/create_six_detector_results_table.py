"""Assemble the six existing detector results without rerunning detectors."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]; L2=ROOT/'layer2_results'
rows=[]

def boot(v):
    rng=np.random.default_rng(2024); return np.array([v[rng.integers(0,len(v),len(v))].mean() for _ in range(10000)])

def add(det, cdu_file, vus_file, hard_file, raw_status, audit_status):
    c=pd.read_csv(cdu_file); v=c[c.folds==5].CDU_bits.to_numpy(float); v10=c[c.folds==10].CDU_bits.to_numpy(float); b=boot(v)
    u=pd.read_csv(vus_file); h=pd.read_csv(hard_file)
    def hv(name):
        q=h[h.subset==name]
        return float(q.VUS_PR_macro.iloc[0]) if len(q) else np.nan
    rows.append(dict(Detector=det,Series=350,Raw_VUS=float(u.VUS_PR.mean()),Raw_VUS_status=raw_status,
        M0_bits=float(c[c.folds==5].L0_bits.mean()),M1_bits=float(c[c.folds==5].L1_bits.mean()),
        CDU_5fold_bits=float(v.mean()),CDU_10fold_bits=float(v10.mean()),CDU_median_5fold=float(np.median(v)),
        CDU_CI_low=float(np.percentile(b,2.5)),CDU_CI_high=float(np.percentile(b,97.5)),
        positive_series_ratio=float((v>0).mean()),bootstrap_prob_macro_positive=float((b>0).mean()),
        Global_Hard20_VUS=hv('Global_Hard20'),Global_Hard30_VUS=hv('Global_Hard30'),Global_Hard50_VUS=hv('Global_Hard50'),
        Family_Hard20_VUS=hv('Family_Hard20'),Family_Hard30_VUS=hv('Family_Hard30'),Easy20_VUS=hv('Easy20'),
        Audit_status=audit_status,CDU_source=str(cdu_file),VUS_source=str(vus_file)))

add('POLY',L2/'audit_cdu_per_series/POLY.csv',L2/'audit_raw_vus_per_series.csv',L2/'POLY_hard_vus.csv','AUDITED raw-window','PASS')
# audit_raw_vus_per_series contains all three detectors; filter below after add correction.
rows[-1]['Raw_VUS']=float(pd.read_csv(L2/'audit_raw_vus_per_series.csv').query("detector=='POLY'").VUS_PR.mean())
add('SubPCA',L2/'audit_cdu_per_series/SubPCA.csv',L2/'audit_raw_vus_per_series.csv',L2/'SubPCA_hard_vus.csv','AUDITED raw-window','PASS')
rows[-1]['Raw_VUS']=float(pd.read_csv(L2/'audit_raw_vus_per_series.csv').query("detector=='SubPCA'").VUS_PR.mean())
add('AnomalyTransformer',L2/'audit_cdu_per_series/AnomalyTransformer.csv',L2/'audit_raw_vus_per_series.csv',L2/'AnomalyTransformer_hard_vus.csv','AUDITED raw-window','FAIL: 2 constant-score series')
rows[-1]['Raw_VUS']=float(pd.read_csv(L2/'audit_raw_vus_per_series.csv').query("detector=='AnomalyTransformer'").VUS_PR.mean())
add('TimesNet',L2/'TimesNet_cdu_per_series.csv',L2/'TimesNet_per_series_vus.csv',L2/'TimesNet_hard_vus.csv','PRELIMINARY legacy offline','NOT AUDITED')
add('MOMENT_ZS',L2/'MOMENT_ZS_audited_cdu_per_series.csv',L2/'MOMENT_ZS_audited_per_series_vus.csv',L2/'MOMENT_ZS_audited_hard_vus.csv','CACHE_OFFLINE raw-window','CACHE_OFFLINE_COMPLETE')
add('MOMENT_FT',L2/'MOMENT_FT_audited_cdu_per_series.csv',L2/'MOMENT_FT_audited_per_series_vus.csv',L2/'MOMENT_FT_audited_hard_vus.csv','CACHE_OFFLINE raw-window','CACHE_OFFLINE_COMPLETE')

df=pd.DataFrame(rows)
df.to_csv(L2/'SIX_DETECTOR_RESULTS.csv',index=False)
md=['# Six detector current results','', 'These are assembled from existing point-score caches and existing offline metric files; no detector was rerun in this step. Raw VUS and hard-VUS status are explicitly labeled because only POLY/SubPCA/AnomalyTransformer had the full raw-window audit, while MOMENT was computed by the cache-offline script and TimesNet remains legacy preliminary.','',df.to_markdown(index=False,floatfmt='.9g'),'','## Per-series files','']
for det in df.Detector:
    if det in ('POLY','SubPCA','AnomalyTransformer'): p=L2/'audit_cdu_per_series'/f'{det}.csv'
    else: p=L2/f'{det}_audited_cdu_per_series.csv' if det.startswith('MOMENT') else L2/f'{det}_cdu_per_series.csv'
    md.append(f'- {det}: `{p}`')
(ROOT/'SIX_DETECTOR_RESULTS.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
print(df.to_string(index=False))
