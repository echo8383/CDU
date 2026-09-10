"""Single-sequence POLY provenance audit.  No benchmark/CDU execution."""
from __future__ import annotations
import hashlib, json, random, sys
from pathlib import Path
import numpy as np, pandas as pd, torch
ROOT=Path(__file__).resolve().parent; REPO=Path(r'D:\CSIES\AI4Energy\others\TSB-AD'); sys.path.insert(0,str(REPO))
from r0_official_compat import find_length_rank_official_compat
from TSB_AD.models.POLY import POLY
from TSB_AD import model_wrapper as mw
from TSB_AD.evaluation.basic_metrics import generate_curve
F='141_MSL_id_2_Sensor_tr_500_1st_550.csv'; d=pd.read_csv(ROOT/'Datasets'/'TSB-AD-U'/F).dropna(); X=d.iloc[:,0:-1].values.astype(float); y=d.Label.astype(int).to_numpy(); W=int(find_length_rank_official_compat(X[:,0].reshape(-1,1),1)); OFF=float(pd.read_csv(ROOT/'uni_vuspr.csv').set_index('file').loc[F,'POLY'])
def h(a): return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def run(name, commit, power, normalize, window, input_variant='raw'):
  z=X.copy()
  if input_variant=='zscore':
    z=(z-z.mean(axis=0))/(z.std(axis=0)+1e-12)
  random.seed(2024); np.random.seed(2024); torch.manual_seed(2024)
  c=POLY(power=power,window=window,normalize=normalize); c.fit(z); s=np.asarray(c.decision_scores_).ravel(); v=float(generate_curve(y,s,window,'opt',250)[7]); return {'variant':name,'poly_implementation':commit,'runner_version':'direct POLY fit + official generate_curve','input_preprocessing':input_variant,'periodicity':1,'power':power,'window':window,'score_hash':h(s),'VUS_PR':v,'official_VUS_PR':OFF,'abs_diff_from_official':abs(v-OFF),'length':len(s),'finite_ratio':float(np.isfinite(s).mean())}
rows=[]
rows.append(run('current_norm_true_power4','8b363e3 current POLY normalize=True',4,True,W))
rows.append(run('pre_f2bf6_norm_false_power4','f2bf6b3^ POLY (no normalize)',4,False,W))
rows.append(run('initial_23d609e_norm_false_power2','23d609e initial POLY + initial optimal HP',2,False,W))
rows.append(run('pre_f2bf6_norm_false_power4_window100','f2bf6b3^ POLY (no normalize)',4,False,100))
rows.append(run('pre_f2bf6_norm_false_power4_zscore','f2bf6b3^ POLY (no normalize)',4,False,W,'zscore'))
pd.DataFrame(rows).to_csv(ROOT/'layer2_results'/'poly_141_provenance_ablation.csv',index=False)
print(pd.DataFrame(rows).to_string(index=False))
