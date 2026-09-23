"""Build a label-free, per-series average-rank interface for all 31 basis curves."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from evaluate_cdu_protocol_v1 import average_rank01, load_source_map
from run_protocol_v1_controls import atomic_json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "layer2_results/basis_scores"
DEST = ROOT / "layer2_results/basis_scores_ranked"
VERSION = "symmetric-rank-basis-v1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    ids = sorted(load_source_map())
    DEST.mkdir(parents=True, exist_ok=True)
    rows = []
    for ordinal, sid in enumerate(ids, 1):
        src = SOURCE / f"{sid}.npz"
        dst = DEST / f"{sid}.npz"
        if dst.exists():
            with np.load(dst, allow_pickle=False) as payload:
                ranked = payload["basis"]
                label = payload["label"]
                names = payload["names"]
            if ranked.shape == (31, len(label)) and np.isfinite(ranked).all():
                rows.append([sid, dst.stat().st_size, dst.stat().st_mtime_ns])
                print(f"[rank-basis] {ordinal}/350 {sid}: SKIP", flush=True)
                continue
        with np.load(src, allow_pickle=False) as payload:
            basis = np.asarray(payload["basis"], dtype=np.float32)
            label = np.asarray(payload["label"], dtype=np.int8)
            names = np.asarray(payload["names"])
        if basis.shape != (31, len(label)) or len(names) != 31:
            raise RuntimeError(f"Invalid basis cache: {sid} {basis.shape}")
        ranked = np.vstack([average_rank01(curve) for curve in basis]).astype(np.float32)
        if not np.isfinite(ranked).all():
            raise RuntimeError(f"Non-finite ranked basis: {sid}")
        temporary = dst.with_suffix(".tmp.npz")
        np.savez_compressed(temporary, basis=ranked, label=label, names=names)
        temporary.replace(dst)
        rows.append([sid, dst.stat().st_size, dst.stat().st_mtime_ns])
        print(f"[rank-basis] {ordinal}/350 {sid}: PASS length={len(label)}", flush=True)
    payload = {
        "version": VERSION,
        "transform": "(average_rank(curve)-0.5)/T independently for each basis curve and series; constants map to 0.5",
        "label_free": True,
        "n_series": len(rows),
        "files": rows,
        "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    payload["manifest_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    atomic_json(payload, DEST / "MANIFEST.json")
    print(f"[rank-basis] COMPLETE 350/350 manifest={payload['manifest_sha256']}", flush=True)


if __name__ == "__main__":
    main()
