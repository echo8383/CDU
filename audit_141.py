import sys, pathlib, pandas as pd, numpy as np, random, torch, hashlib
root=pathlib.Path(__file__).resolve().parent; repo=pathlib.Path(r'D:\CSIES\AI4Energy\others\TSB-AD'); sys.path.insert(0,str(repo))
from r0_official_compat import find_length_rank_official_compat as fw
from TSB_AD import model_wrapper as mw
from TSB_AD.HP_list import Optimal_Uni_algo_HP_dict as hp
from TSB_AD.evaluation.basic_metrics import generate_curve
from TSB_AD.models.POLY import POLY
f='141_MSL_id_2_Sensor_tr_500_1st_550.csv'; d=pd.read_csv(root/'Datasets'/'TSB-AD-U'/f).dropna(); data=d.iloc[:,:-1].values.astype(float); y=d.Label.to_numpy(int); w=fw(data[:,0].reshape(-1,1),1); print('shape',data.shape,'w',w,'official',pd.read_csv(root/'uni_vuspr.csv').set_index('file').loc[f,'POLY'])
for k in range(2):
 random.seed(2024); np.random.seed(2024); torch.manual_seed(2024); mw.find_length_rank=fw; s=np.asarray(mw.run_Unsupervise_AD('POLY',data,**hp['POLY']),float).ravel(); print(k,len(s),np.isfinite(s).mean(),s[:10], 'hash',hashlib.sha256(s.tobytes()).hexdigest(), 'vus',generate_curve(y,s,w,'opt',250)[7], 'v100',generate_curve(y,s,100,'opt',250)[7])
for norm in [False, True]:
 random.seed(2024); np.random.seed(2024); torch.manual_seed(2024)
 clf=POLY(power=4, window=w, normalize=norm); clf.fit(data); s=np.asarray(clf.decision_scores_,float).ravel(); print('direct normalize',norm,'hash',hashlib.sha256(s.tobytes()).hexdigest(),'vus',generate_curve(y,s,w,'opt',250)[7])
