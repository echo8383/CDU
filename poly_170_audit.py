import sys, pathlib, pandas as pd, numpy as np, random, torch, hashlib
root=pathlib.Path(__file__).resolve().parent; repo=pathlib.Path(r'D:\CSIES\AI4Energy\others\TSB-AD'); sys.path.insert(0,str(repo))
from r0_official_compat import find_length_rank_official_compat as fw
from TSB_AD.models.POLY import POLY
from TSB_AD.evaluation.basic_metrics import generate_curve
f='170_MITDB_id_1_Medical_tr_17675_1st_17775.csv'; d=pd.read_csv(root/'Datasets'/'TSB-AD-U'/f).dropna(); X=d.iloc[:,:-1].values.astype(float); y=d.Label.to_numpy(int); w=fw(X[:,0].reshape(-1,1),1); off=float(pd.read_csv(root/'uni_vuspr.csv').set_index('file').loc[f,'POLY']); print('shape',X.shape,'window',w,'official',off)
def run(name,power,norm,win,inp):
 z=X.copy()
 if inp=='zscore': z=(z-z.mean(0))/(z.std(0)+1e-12)
 random.seed(2024); np.random.seed(2024); torch.manual_seed(2024); c=POLY(power=power,window=win,normalize=norm); c.fit(z); s=np.asarray(c.decision_scores_).ravel(); v=float(generate_curve(y,s,win,'opt',250)[7]); print(name, 'power',power,'norm',norm,'win',win,'inp',inp,'hash',hashlib.sha256(s.tobytes()).hexdigest(),'vus',v,'diff',abs(v-off))
run('historical_p4',4,False,w,'raw'); run('current_p4',4,True,w,'raw'); run('historical_p2',2,False,w,'raw'); run('historical_p4_w100',4,False,100,'raw'); run('historical_p4_zscore',4,False,w,'zscore')
