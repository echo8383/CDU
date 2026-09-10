"""Pinned TSB-AD FITS adapter (frequency-interpolation reconstruction score)."""
from __future__ import annotations
import hashlib, json, time
import numpy as np
from .common import run

NAME = "FITS"
MODE = "train-then-score"
PINNED_CONFIG = {"win_size": 100, "lr": 1e-3}
SOURCE_COMMIT = "d040bb015b6299da26d879b90dd19c80fb72c160"
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
