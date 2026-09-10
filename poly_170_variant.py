import sys,pathlib,pandas as pd,numpy as np,random,torch,hashlib,argparse
root=pathlib.Path(__file__).resolve().parent; repo=pathlib.Path(r'D:\CSIES\AI4Energy\others\TSB-AD'); sys.path.insert(0,str(repo))
from r0_official_compat import find_length_rank_official_compat as fw
from TSB_AD.models.POLY import POLY
from TSB_AD.evaluation.basic_metrics import generate_curve
ap=argparse.ArgumentParser();ap.add_argument('--power',type=int);ap.add_argument('--norm',action='store_true');a=ap.parse_args();f='170_MITDB_id_1_Medical_tr_17675_1st_17775.csv';d=pd.read_csv(root/'Datasets'/'TSB-AD-U'/f).dropna();X=d.iloc[:,:-1].values.astype(float);y=d.Label.to_numpy(int);w=fw(X[:,0].reshape(-1,1),1);off=float(pd.read_csv(root/'uni_vuspr.csv').set_index('file').loc[f,'POLY']);random.seed(2024);np.random.seed(2024);torch.manual_seed(2024);c=POLY(power=a.power,window=w,normalize=a.norm);c.fit(X);s=np.asarray(c.decision_scores_).ravel();v=generate_curve(y,s,w,'opt',250)[7];print({'power':a.power,'norm':a.norm,'window':w,'vus':float(v),'official':off,'diff':abs(float(v)-off),'hash':hashlib.sha256(s.tobytes()).hexdigest()},flush=True)
