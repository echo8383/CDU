from pathlib import Path
import pandas as pd
p=Path(__file__).resolve().parents[1]/'stage3_results'
for k in range(5):
 f=p/f'ensemble_vus_fold{k}.csv'
 if f.exists():
  try: print(f'fold {k+1}: {len(pd.read_csv(f))}/70 ensemble-VUS series cached')
  except Exception as e: print(f'fold {k+1}: unreadable: {e}')
 else: print(f'fold {k+1}: not started')
for f in ['STAGE3_ENSEMBLE_RESULTS.csv','CDU_SELECTION_PATH.csv','RAW_VUS_SELECTION_PATH.csv','RANDOM_SELECTION_RESULTS.csv','ORACLE_UPPER_BOUND.csv','STAGE3_ENSEMBLE_BOOTSTRAP.csv']:
 q=p/f; print(f'{f}: '+('present' if q.exists() else 'pending'))
