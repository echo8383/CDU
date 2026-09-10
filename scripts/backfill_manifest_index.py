from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; files=pd.read_csv(ROOT/'uni_vuspr.csv').file.tolist()
for name in ['AnomalyTransformer','SubPCA','TimesNet','MOMENT_ZS','MOMENT_FT']:
 p=ROOT/'layer2_results'/f'{name}_score_manifest.csv'
 if not p.exists(): continue
 r=pd.read_csv(p); r['series_index']=r.series_id.map({f:i+1 for i,f in enumerate(files)}); r['total_series']=len(files); cols=['detector','series_index','total_series']+[c for c in r.columns if c not in {'detector','series_index','total_series'}]; r[cols].to_csv(p,index=False); print(name,len(r),r.series_index.min(),r.series_index.max())
