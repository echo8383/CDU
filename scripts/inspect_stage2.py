import pandas as pd
for p in ['layer2_results/audit_raw_vus_per_series.csv','layer2_results/STAGE2_RAW_VUS_RECOMPUTED.csv']:
    x=pd.read_csv(p); print(p, x.columns.tolist()); print(x.groupby('detector').VUS_PR.mean() if 'VUS_PR' in x else x.to_string(index=False))
for p in ['layer2_results/FITS_per_series_vus.csv','layer2_results/M2N2_per_series_vus.csv','layer2_results/TimesNet_per_series_vus.csv','layer2_results/POLY_per_series_vus.csv']:
 x=pd.read_csv(p); print(p,x.columns.tolist(),x.head(1).to_dict('records'))
