"""Source-LOSO reconstruction of nine detector scores from the ranked basis.

One fixed multi-output ridge model is fitted per held-out source. Training uses
the approved deterministic cap; every test timestamp is predicted and cached.
"""
from __future__ import annotations

import gc
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from threadpoolctl import threadpool_limits

from evaluate_cdu_protocol_v1 import CACHE_DIRS, DETECTORS, average_rank01, load_source_map
from run_probe_robustness import sample_indices, weights
from run_protocol_v1_controls import atomic_csv, atomic_json
from run_symmetric_rank import RANKED, read_ranked_basis

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "protocol_score_decomposition/cap2048"
VERSION = "score-decomposition-ridge-cap2048-v1"
ALPHA = 1.0
CAP = 2048


def score_matrix(sid: str, length: int) -> np.ndarray:
    columns = []
    for detector in DETECTORS:
        raw = np.load(CACHE_DIRS[detector] / f"{sid}.npy", allow_pickle=False)
        if raw.ndim != 1 or len(raw) != length or not np.isfinite(raw).all():
            raise RuntimeError(f"Invalid score: {detector}/{sid}")
        columns.append(average_rank01(raw).astype(np.float32))
    return np.column_stack(columns)


def valid_source(source: str, expected: list[str], signature: str) -> bool:
    csv_path = OUT / "by_source" / f"{source}.csv"
    json_path = csv_path.with_suffix(".json")
    if not csv_path.exists() or not json_path.exists():
        return False
    if json.loads(json_path.read_text()).get("signature") != signature:
        raise RuntimeError(f"Checkpoint signature mismatch: {source}")
    frame = pd.read_csv(csv_path)
    if set(frame.series_id) != set(expected) or len(frame) != len(expected) * len(DETECTORS):
        raise RuntimeError(f"Invalid decomposition checkpoint: {source}")
    for detector in DETECTORS:
        for sid in expected:
            if not (OUT / "predicted" / detector / f"{sid}.npy").exists():
                return False
            if not (OUT / "residual" / detector / f"{sid}.npy").exists():
                return False
    return True


def main():
    manifest_path = RANKED / "MANIFEST.json"
    if not manifest_path.exists():
        raise RuntimeError("Ranked basis cache is not ready")
    ranked_manifest = json.loads(manifest_path.read_text())
    mapping = load_source_map()
    ids, sources = sorted(mapping), sorted(set(mapping.values()))
    cache_identity = []
    for detector in DETECTORS:
        for sid in ids:
            path = CACHE_DIRS[detector] / f"{sid}.npy"
            cache_identity.append([path.relative_to(ROOT).as_posix(), path.stat().st_size, path.stat().st_mtime_ns])
    signature_payload = {
        "version": VERSION, "alpha": ALPHA, "training_cap_per_series": CAP,
        "ranked_basis_manifest": ranked_manifest["manifest_sha256"],
        "source_map_sha256": hashlib.sha256((ROOT / "source_groups.json").read_bytes()).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "detector_cache_identity": cache_identity,
    }
    signature = hashlib.sha256(json.dumps(signature_payload, sort_keys=True).encode()).hexdigest()
    run_manifest = OUT / "RUN_MANIFEST.json"
    if run_manifest.exists():
        if json.loads(run_manifest.read_text()).get("signature") != signature:
            raise RuntimeError("Decomposition identity changed; refusing mixed results")
    else:
        atomic_json({**signature_payload, "signature": signature}, run_manifest)

    lengths = pd.read_csv(ROOT / "protocol_fast_results/shared_baseline/PER_SERIES.csv").set_index("series_id").n_points
    total = sum(min(int(lengths[sid]), CAP) for sid in ids)
    x_train = np.empty((total, 31), np.float32)
    s_train = np.empty((total, len(DETECTORS)), np.float32)
    rows, cursor = [], 0
    for ordinal, sid in enumerate(ids, 1):
        basis, labels, _ = read_ranked_basis(sid)
        index = sample_indices(sid, len(labels), CAP, VERSION)
        end = cursor + len(index)
        x_train[cursor:end] = basis[index]
        s_train[cursor:end] = score_matrix(sid, len(labels))[index]
        rows.append({"series_id": sid, "source": mapping[sid], "start": cursor,
                     "end": end, "n_full": len(labels)})
        cursor = end
        if ordinal % 50 == 0:
            print(f"[decomposition/prepare] {ordinal}/350 points={cursor}", flush=True)
    del basis, labels, index
    gc.collect()

    for detector in DETECTORS:
        (OUT / "predicted" / detector).mkdir(parents=True, exist_ok=True)
        (OUT / "residual" / detector).mkdir(parents=True, exist_ok=True)
    all_rows = []
    for fold, source in enumerate(sources, 1):
        test_rows = [row for row in rows if row["source"] == source]
        expected = [row["series_id"] for row in test_rows]
        if valid_source(source, expected, signature):
            print(f"[decomposition] {fold}/23 {source}: SKIP", flush=True)
            all_rows.append(pd.read_csv(OUT / "by_source" / f"{source}.csv"))
            continue
        train = [row for row in rows if row["source"] != source]
        train_index = np.concatenate([np.arange(row["start"], row["end"]) for row in train])
        sample_weight = weights(train)
        started = time.perf_counter()
        print(f"[decomposition] {fold}/23 {source}: FIT n={len(train_index)} targets=9", flush=True)
        model = Ridge(alpha=ALPHA, fit_intercept=True, solver="auto").fit(
            x_train[train_index], s_train[train_index], sample_weight=sample_weight)
        del train_index, sample_weight
        gc.collect()
        output = []
        for row in test_rows:
            sid = row["series_id"]
            basis, labels, _ = read_ranked_basis(sid)
            observed = score_matrix(sid, len(labels))
            predicted = np.asarray(model.predict(basis), dtype=np.float32)
            residual = observed - predicted
            for column, detector in enumerate(DETECTORS):
                pred = predicted[:, column]
                resid = residual[:, column]
                np.save(OUT / "predicted" / detector / f"{sid}.npy", pred, allow_pickle=False)
                np.save(OUT / "residual" / detector / f"{sid}.npy", resid, allow_pickle=False)
                target = observed[:, column]
                denominator = float(np.sum((target - target.mean()) ** 2))
                r2 = np.nan if denominator == 0 else 1.0 - float(np.sum((target - pred) ** 2)) / denominator
                rho = np.nan if np.ptp(target) == 0 or np.ptp(pred) == 0 else float(spearmanr(target, pred).statistic)
                output.append({"series_id": sid, "source_dataset": source, "detector": detector,
                               "n_points": len(labels), "R2": r2, "Spearman": rho,
                               "MSE": float(np.mean((target - pred) ** 2)),
                               "predicted_hash": hashlib.sha256(pred.tobytes()).hexdigest(),
                               "residual_hash": hashlib.sha256(resid.tobytes()).hexdigest()})
        elapsed = time.perf_counter() - started
        frame = pd.DataFrame(output)
        atomic_csv(frame, OUT / "by_source" / f"{source}.csv")
        atomic_json({"signature": signature, "test_source": source,
                     "training_sources": sorted({row['source'] for row in train}),
                     "runtime_seconds": elapsed, "alpha": ALPHA,
                     "training_cap": CAP, "test_points": "all"},
                    OUT / "by_source" / f"{source}.json")
        all_rows.append(frame)
        print(f"[decomposition] {fold}/23 {source}: PASS runtime={elapsed:.1f}s series={len(test_rows)}", flush=True)
        del model, predicted, residual, observed, basis, labels
        gc.collect()

    combined = pd.concat(all_rows, ignore_index=True)
    atomic_csv(combined, OUT / "PER_SERIES.csv")
    source = combined.groupby(["detector", "source_dataset"], as_index=False).agg(
        R2=("R2", "mean"), Spearman=("Spearman", "mean"), MSE=("MSE", "mean"),
        n_series=("series_id", "count"))
    summary = source.groupby("detector", as_index=False).agg(
        source_macro_R2=("R2", "mean"), source_macro_Spearman=("Spearman", "mean"),
        source_macro_MSE=("MSE", "mean"), n_sources=("source_dataset", "count"))
    summary["finite_R2_series"] = combined.groupby("detector").R2.apply(lambda x: int(np.isfinite(x).sum())).values
    summary["finite_Spearman_series"] = combined.groupby("detector").Spearman.apply(lambda x: int(np.isfinite(x).sum())).values
    atomic_csv(source, OUT / "PER_SOURCE.csv")
    atomic_csv(summary, OUT / "SUMMARY.csv")
    atomic_json({"status": "COMPLETE", "signature": signature}, OUT / "QUEUE_STATUS.json")
    print("[decomposition] COMPLETE\n" + summary.to_string(index=False), flush=True)


if __name__ == "__main__":
    with threadpool_limits(limits=4):
        main()
