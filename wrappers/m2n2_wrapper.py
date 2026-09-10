"""Pinned TSB-AD M2N2 adapter.

M2N2 is train-then-score with explicit online test-time adaptation.  A fresh
TSB-AD model is created for every call/series by ``run_M2N2``; labels never
enter fitting, threshold estimation, or adaptation.
"""
from __future__ import annotations
import hashlib, json, time
import numpy as np
from .common import run

NAME = "M2N2"
MODE = "train-then-score + online test-time adaptation"
PINNED_CONFIG = {"win_size": 12, "stride": 12, "batch_size": 64,
                 "epochs": 100, "latent_dim": 16, "lr": 1e-3,
                 "ttlr": 1e-3, "normalization": "Detrend", "gamma": 0.99,
                 "th": 0.9, "valid_size": 0.2, "infer_mode": "online"}
SOURCE_COMMIT = "616b2270b6f2eab88ee5caa37c45507d2d041d22"
TSBAD_COMMIT = "8b363e350ae047a8115a594d1e9da64aae09b852"

def run_detector(train_data, test_data, config=None, seed=2024, device=None):
    cfg = dict(PINNED_CONFIG); cfg.update(config or {})
    t = time.time(); score, used = run(NAME, train_data, test_data, cfg, seed)
    score = np.asarray(score, dtype=float).ravel()
    ch = hashlib.sha256(json.dumps(used, sort_keys=True).encode()).hexdigest()
    return {"score": score, "metadata": {"detector": NAME, "seed": seed,
        "config": used, "config_hash": ch, "train_length": len(train_data),
        "test_length": len(test_data), "score_length": len(score),
        "runtime_sec": time.time()-t, "device": str(device or "TSB-AD auto"),
        "mode": MODE, "source_commit": SOURCE_COMMIT, "tsbad_commit": TSBAD_COMMIT}}
