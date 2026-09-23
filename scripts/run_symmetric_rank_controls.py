"""Matching duplicate/noise/synthetic controls for the symmetric rank-basis interface."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

import run_basis_sensitivity as engine
from evaluate_cdu_protocol_v1 import average_rank01, load_source_map
from run_protocol_fast import deterministic_noise
from run_symmetric_rank import RANKED, read_ranked_basis

ROOT = Path(__file__).resolve().parents[1]
CONTROL_ROOT = ROOT / "layer2_results/symmetric_rank_controls"
CONTROLS = ("duplicate_Var96", "independent_noise", "complementary_alpha2")


def build_controls():
    for name in CONTROLS:
        (CONTROL_ROOT / name).mkdir(parents=True, exist_ok=True)
    for ordinal, sid in enumerate(sorted(load_source_map()), 1):
        basis, labels, names = read_ranked_basis(sid)
        values = {
            "duplicate_Var96": basis[:, names.index("Var-96")],
            "independent_noise": average_rank01(deterministic_noise(sid, "independent_noise", len(labels))),
            "complementary_alpha2": average_rank01(
                deterministic_noise(sid, "complementary", len(labels)) + 2.0 * labels),
        }
        for name, score in values.items():
            path = CONTROL_ROOT / name / f"{sid}.npy"
            if not path.exists():
                np.save(path, np.asarray(score, dtype=np.float32), allow_pickle=False)
        if ordinal % 50 == 0 or ordinal == 350:
            print(f"[symmetric-controls/cache] {ordinal}/350", flush=True)


def main():
    manifest = json.loads((RANKED / "MANIFEST.json").read_text())
    build_controls()
    wrapper_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    engine.VERSION = f"symmetric-rank-controls-cap2048-v1|{manifest['manifest_sha256']}|{wrapper_hash}"
    engine.FAMILIES["symmetric_rank_controls"] = ("__retain_all_columns__",)
    engine.keep_columns = lambda names, family: np.ones(len(names), dtype=bool)
    engine.read_basis = read_ranked_basis
    engine.DETECTORS = CONTROLS
    for name in CONTROLS:
        engine.CACHE_DIRS[name] = CONTROL_ROOT / name
    with threadpool_limits(limits=2):
        engine.run("symmetric_rank_controls", 2048, 0)


if __name__ == "__main__":
    main()
