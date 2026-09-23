"""Run accelerated source-LOSO CDU with a symmetric rank interface for B and S_D."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

import run_basis_sensitivity as engine

ROOT = Path(__file__).resolve().parents[1]
RANKED = ROOT / "layer2_results/basis_scores_ranked"


def read_ranked_basis(sid):
    with np.load(RANKED / f"{sid}.npz", allow_pickle=False) as payload:
        basis = payload["basis"]
        labels = payload["label"].astype(np.int8)
        names = tuple(map(str, payload["names"]))
    if basis.shape != (31, len(labels)):
        raise RuntimeError(f"Invalid ranked basis: {sid} {basis.shape}")
    basis = basis.T
    if not np.isfinite(basis).all() or not np.isin(labels, [0, 1]).all():
        raise RuntimeError(f"Invalid ranked data: {sid}")
    return np.asarray(basis, dtype=np.float32), labels, names


def main():
    manifest_path = RANKED / "MANIFEST.json"
    if not manifest_path.exists():
        raise RuntimeError("Run build_ranked_basis_cache.py first")
    manifest = json.loads(manifest_path.read_text())
    wrapper_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    engine.VERSION = f"symmetric-rank-cap2048-v1|{manifest['manifest_sha256']}|{wrapper_hash}"
    engine.FAMILIES["symmetric_rank"] = ("__retain_all_columns__",)
    engine.keep_columns = lambda names, family: np.ones(len(names), dtype=bool)
    engine.read_basis = read_ranked_basis
    with threadpool_limits(limits=2):
        engine.run("symmetric_rank", 2048, 0)


if __name__ == "__main__":
    main()
