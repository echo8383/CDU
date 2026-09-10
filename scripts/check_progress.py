from pathlib import Path
import pandas as pd
p=Path('layer2_results/stage2_raw_vus_per_series')
for f in ['M2N2','TranAD','TimesNet','FITS']:
 q=p/(f+'.csv')
 if q.exists():
  x=pd.read_csv(q); good=x['status'].eq('PASS').sum(); print(f, 'rows',len(x),'pass',good,'done',good,'/350','last',x[x.status.eq('PASS')].series_id.iloc[-1] if good else '-')
 else: print(f,'missing')
