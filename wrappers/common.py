from __future__ import annotations
import os, random, sys
from pathlib import Path
import numpy as np
import torch

def _resolve_tsb_ad_root() -> Path:
    """Resolve the external TSB-AD checkout without embedding a user path."""
    configured = os.environ.get("TSB_AD_ROOT")
    if configured:
        candidate = Path(configured).expanduser()
        if (candidate / "TSB_AD").is_dir():
            return candidate.resolve()
    raise RuntimeError(
        "TSB-AD checkout not found. Set TSB_AD_ROOT to the directory containing "
        "the TSB_AD package (for example: $env:TSB_AD_ROOT='D:\\repos\\TSB-AD')."
    )

REPO = _resolve_tsb_ad_root()
if str(REPO) not in sys.path: sys.path.insert(0,str(REPO))
from TSB_AD import model_wrapper as mw
from TSB_AD.HP_list import Optimal_Uni_algo_HP_dict
from cdu.tsb_ad_compat import patch_model_wrapper
patch_model_wrapper(mw)

def seed_all(seed=2024):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark=False; torch.backends.cudnn.deterministic=True

def run(name: str, train_data: np.ndarray, test_data: np.ndarray, config=None, seed=2024):
    """Return a point-wise score without changing the source detector protocol.

    `test_data` is the complete labeled evaluation sequence, matching
    Run_Detector_U.py.  For semi-supervised detectors train_data is the
    filename-derived prefix; unsupervised detectors receive full test_data.
    """
    seed_all(seed); cfg=dict(Optimal_Uni_algo_HP_dict[name] if config is None else config)
    if name in mw.Semisupervise_AD_Pool:
        out=mw.run_Semisupervise_AD(name, train_data, test_data, **cfg)
    elif name in mw.Unsupervise_AD_Pool:
        out=mw.run_Unsupervise_AD(name, test_data, **cfg)
    else: raise ValueError(f'Unknown TSB-AD detector {name}')
    if not isinstance(out,np.ndarray): raise RuntimeError(str(out))
    return np.asarray(out,dtype=float).ravel(), cfg
