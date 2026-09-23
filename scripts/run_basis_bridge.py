"""Matched series-CV bridge for basis utility under legacy and rank interfaces."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold
from threadpoolctl import threadpool_limits

from evaluate_cdu_protocol_v1 import load_source_map, log_loss_bits, make_probe
from run_probe_robustness import read_basis, sample_indices
from run_protocol_v1_controls import atomic_csv, atomic_json
from run_symmetric_rank import read_ranked_basis

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "protocol_basis_bridge/cap2048"
CAP = 2048
VERSION = "matched-series-cv-basis-bridge-v1"


def series_weights(rows):
    total = sum(row["end"] - row["start"] for row in rows)
    return np.concatenate([np.full(row["end"] - row["start"],
        total / (len(rows) * (row["end"] - row["start"])), dtype=float) for row in rows])


def main():
    mapping = load_source_map()
    ids = sorted(mapping)
    lengths = pd.read_csv(ROOT / "protocol_fast_results/shared_baseline/PER_SERIES.csv").set_index("series_id").n_points
    total = sum(min(int(lengths[sid]), CAP) for sid in ids)
    x_raw = np.empty((total, 31), np.float32)
    x_rank = np.empty((total, 31), np.float32)
    labels_train = np.empty(total, np.int8)
    rows, cursor = [], 0
    for ordinal, sid in enumerate(ids, 1):
        raw, labels, _ = read_basis(sid)
        ranked, labels2, _ = read_ranked_basis(sid)
        if not np.array_equal(labels, labels2):
            raise RuntimeError(f"Label mismatch: {sid}")
        index = sample_indices(sid, len(labels), CAP, VERSION)
        end = cursor + len(index)
        x_raw[cursor:end], x_rank[cursor:end] = raw[index], ranked[index]
        labels_train[cursor:end] = labels[index]
        rows.append({"series_id": sid, "source_dataset": mapping[sid], "start": cursor,
                     "end": end, "n_full": len(labels)})
        cursor = end
        if ordinal % 50 == 0:
            print(f"[bridge/prepare] {ordinal}/350 points={cursor}", flush=True)
    results = []
    for folds in (5, 10):
        splitter = KFold(n_splits=folds, shuffle=True, random_state=2024)
        for fold, (train_idx, test_idx) in enumerate(splitter.split(ids), 1):
            train = [rows[i] for i in train_idx]
            test = [rows[i] for i in test_idx]
            point_index = np.concatenate([np.arange(row["start"], row["end"]) for row in train])
            w = series_weights(train)
            y = labels_train[point_index]
            prior = float(np.clip(np.average(y, weights=w), 1e-7, 1 - 1e-7))
            for interface, matrix, reader in (("legacy", x_raw, read_basis),
                                               ("symmetric_rank", x_rank, read_ranked_basis)):
                started = time.perf_counter()
                print(f"[bridge/{interface}/{folds}fold] {fold}/{folds}: FIT n={len(point_index)}", flush=True)
                model = make_probe(0.1).fit(matrix[point_index], y, sample_weight=w)
                for row in test:
                    basis, labels, _ = reader(row["series_id"])
                    lb = log_loss_bits(labels, model.predict_proba(basis)[:, 1])
                    l0 = log_loss_bits(labels, np.full(len(labels), prior))
                    results.append({"series_id": row["series_id"], "source_dataset": row["source_dataset"],
                                    "folds": folds, "fold": fold, "interface": interface,
                                    "L_prior": l0, "L_basis": lb, "basis_utility": l0 - lb,
                                    "n_points": len(labels)})
                print(f"[bridge/{interface}/{folds}fold] {fold}/{folds}: PASS runtime={time.perf_counter()-started:.1f}s", flush=True)
            del point_index, w, y
    frame = pd.DataFrame(results)
    atomic_csv(frame, OUT / "PER_SERIES.csv")
    summaries = []
    for (folds, interface), group in frame.groupby(["folds", "interface"]):
        values = group.basis_utility.to_numpy()
        boot = values[np.random.default_rng(2024).integers(0, len(values), size=(10000, len(values)))].mean(axis=1)
        summaries.append({"folds": folds, "interface": interface,
                          "L_prior": group.L_prior.mean(), "L_basis": group.L_basis.mean(),
                          "basis_utility": values.mean(),
                          "CI_low": np.quantile(boot, .025), "CI_high": np.quantile(boot, .975),
                          "positive_series": int((values > 0).sum()), "n_series": len(group)})
    summary = pd.DataFrame(summaries)
    atomic_csv(summary, OUT / "SUMMARY.csv")
    signature = hashlib.sha256((VERSION + Path(__file__).read_text()).encode()).hexdigest()
    atomic_json({"status": "COMPLETE", "version": VERSION, "signature": signature,
                 "training_cap": CAP, "test_points": "all", "fold_seed": 2024}, OUT / "QUEUE_STATUS.json")
    print("[bridge] COMPLETE\n" + summary.to_string(index=False), flush=True)


if __name__ == "__main__":
    with threadpool_limits(limits=4):
        main()
