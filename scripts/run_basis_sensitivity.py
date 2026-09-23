"""Resumable leave-one-basis-family-out CDU sensitivity on frozen caches.

The detector outputs, source-LOSO split, fixed logistic probe, test population,
and source-macro aggregation are unchanged.  Training uses the same deterministic
per-series cap as the approved accelerated probe-robustness branch; every test
timestamp is retained.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits

from evaluate_cdu_protocol_v1 import (
    CACHE_DIRS,
    DETECTORS,
    average_rank01,
    load_source_map,
    log_loss_bits,
    make_probe,
)
from run_probe_robustness import read_basis, sample_indices, weights
from run_protocol_v1_controls import atomic_csv, atomic_json


ROOT = Path(__file__).resolve().parents[1]
VERSION = "basis-sensitivity-cap2048-v1"
FAMILIES = {
    "variance": ("Var-",),
    "range": ("Range-",),
    "next_difference": ("Last-",),
    "centered_placement": ("Centered-",),
    "absolute_difference": ("AbsDiff-",),
    "mad": ("MAD-",),
    "spectral_entropy": ("SpecEnt-",),
}


def keep_columns(names: tuple[str, ...], family: str) -> np.ndarray:
    prefixes = FAMILIES[family]
    keep = np.asarray([not any(name.startswith(p) for p in prefixes) for name in names])
    if keep.sum() == 0 or keep.all():
        raise RuntimeError(f"Invalid family definition: {family}")
    return keep


def checkpoint(path: Path, signature: str, expected: set[str]):
    meta = path.with_suffix(".json")
    if not path.exists() or not meta.exists():
        return None
    payload = json.loads(meta.read_text())
    if payload.get("signature") != signature:
        raise RuntimeError(f"Checkpoint signature mismatch: {path}")
    frame = pd.read_csv(path)
    if not frame.series_id.is_unique or set(frame.series_id) != expected:
        raise RuntimeError(f"Invalid checkpoint population: {path}")
    if not np.isfinite(frame.select_dtypes(include=[np.number]).to_numpy()).all():
        raise RuntimeError(f"Non-finite checkpoint: {path}")
    return frame


def summarize(directory: Path, sources: list[str], signature: str, detector: str):
    paths = [directory / "by_source" / f"{source}.csv" for source in sources]
    if not all(path.exists() for path in paths):
        return
    frame = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
    if len(frame) != 350 or frame.series_id.nunique() != 350:
        raise RuntimeError(f"Incomplete summary population: {directory}")
    np.testing.assert_allclose(frame.CDU, frame.L_basis - frame.L_basis_detector, atol=1e-14)
    source = frame.groupby("source_dataset", as_index=False).agg(
        L_basis=("L_basis", "mean"),
        L_basis_detector=("L_basis_detector", "mean"),
        CDU=("CDU", "mean"),
        n_series=("series_id", "count"),
    )
    values = source.CDU.to_numpy()
    draws = np.random.default_rng(2024).integers(0, len(values), size=(10000, len(values)))
    boot = values[draws].mean(axis=1)
    lo, hi = np.quantile(boot, (0.025, 0.975))
    summary = pd.DataFrame([{
        "detector": detector,
        "CDU": values.mean(),
        "CDU_CI_low": lo,
        "CDU_CI_high": hi,
        "positive_sources": int((values > 0).sum()),
        "bootstrap_prob_source_macro_positive": float((boot > 0).mean()),
        "n_series": 350,
        "n_sources": len(values),
        "signature": signature,
    }])
    atomic_csv(frame, directory / "PER_SERIES.csv")
    atomic_csv(source, directory / "PER_SOURCE.csv")
    atomic_csv(summary, directory / "SUMMARY.csv")


def run(family: str, cap: int, max_new_folds: int):
    mapping = load_source_map()
    ids = sorted(mapping)
    sources = sorted(set(mapping.values()))
    result_root = ROOT / "protocol_basis_results" / f"cap{cap}" / f"drop_{family}"
    input_paths = [ROOT / "layer2_results/basis_scores" / f"{sid}.npz" for sid in ids]
    input_paths += [CACHE_DIRS[d] / f"{sid}.npy" for d in DETECTORS for sid in ids]
    signature_payload = {
        "version": VERSION,
        "family": family,
        "training_cap_per_series": cap,
        "probe": {"kind": "logistic", "C": 0.1, "solver": "liblinear", "max_iter": 300},
        "source_map_hash": hashlib.sha256((ROOT / "source_groups.json").read_bytes()).hexdigest(),
        "runner_hash": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "input_identity": [[p.relative_to(ROOT).as_posix(), p.stat().st_size, p.stat().st_mtime_ns]
                           for p in input_paths],
    }
    signature = hashlib.sha256(json.dumps(signature_payload, sort_keys=True).encode()).hexdigest()
    manifest = result_root / "RUN_MANIFEST.json"
    if manifest.exists():
        if json.loads(manifest.read_text()).get("signature") != signature:
            raise RuntimeError(f"Existing result identity differs: {result_root}")
    else:
        atomic_json({**signature_payload, "signature": signature}, manifest)

    lengths = pd.read_csv(ROOT / "protocol_fast_results/shared_baseline/PER_SERIES.csv").set_index("series_id").n_points
    total = sum(min(int(lengths[sid]), cap) for sid in ids)
    y_train = np.empty(total, np.int8)
    rows, cursor, names0, keep = [], 0, None, None
    # Determine retained dimensionality before allocation.
    _, _, names0 = read_basis(ids[0])
    keep = keep_columns(names0, family)
    basis_train = np.empty((total, int(keep.sum())), np.float32)
    for ordinal, sid in enumerate(ids, 1):
        basis, labels, names = read_basis(sid)
        if names != names0:
            raise RuntimeError(f"Basis names differ: {sid}")
        index = sample_indices(sid, len(labels), cap, VERSION)
        end = cursor + len(index)
        basis_train[cursor:end] = basis[index][:, keep]
        y_train[cursor:end] = labels[index]
        rows.append({"series_id": sid, "source": mapping[sid], "start": cursor,
                     "end": end, "n_full": len(labels)})
        cursor = end
        if ordinal % 50 == 0:
            print(f"[{family}/prepare] {ordinal}/350 points={cursor} p={keep.sum()}", flush=True)
    del basis, labels, index
    gc.collect()

    new_folds = 0
    tasks = ["baseline"] + list(DETECTORS)
    for task in tasks:
        directory = result_root / task
        if task != "baseline" and (directory / "SUMMARY.csv").exists():
            print(f"[{family}/{task}] COMPLETE: SKIP", flush=True)
            continue
        scores = None
        if task != "baseline":
            scores = np.empty(total, np.float32)
            for row in rows:
                raw = np.load(CACHE_DIRS[task] / f"{row['series_id']}.npy", allow_pickle=False)
                if raw.ndim != 1 or len(raw) != row["n_full"] or not np.isfinite(raw).all():
                    raise RuntimeError(f"Invalid score: {task}/{row['series_id']}")
                score = average_rank01(raw).astype(np.float32)
                index = sample_indices(row["series_id"], len(raw), cap, VERSION)
                scores[row["start"]:row["end"]] = score[index]
        for number, source in enumerate(sources, 1):
            path = directory / "by_source" / f"{source}.csv"
            test_rows = [row for row in rows if row["source"] == source]
            expected = {row["series_id"] for row in test_rows}
            if checkpoint(path, signature, expected) is not None:
                print(f"[{family}/{task}] {number}/23 {source}: SKIP", flush=True)
                continue
            train = [row for row in rows if row["source"] != source]
            x = np.concatenate([basis_train[row["start"]:row["end"]] for row in train])
            if task != "baseline":
                detector_feature = np.concatenate([scores[row["start"]:row["end"]] for row in train])
                x = np.column_stack((x, detector_feature))
            labels = np.concatenate([y_train[row["start"]:row["end"]] for row in train])
            sample_weight = weights(train)
            print(f"[{family}/{task}] {number}/23 {source}: FIT n={len(x)} p={x.shape[1]}", flush=True)
            started = time.perf_counter()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ConvergenceWarning)
                model = make_probe(0.1).fit(x, labels, sample_weight=sample_weight)
            del x, labels, sample_weight
            gc.collect()
            reference = None
            if task != "baseline":
                reference_path = result_root / "baseline/by_source" / f"{source}.csv"
                reference = checkpoint(reference_path, signature, expected)
                if reference is None:
                    raise RuntimeError(f"Missing matching baseline: {source}")
                reference = reference.set_index("series_id")
            output = []
            for row in test_rows:
                sid = row["series_id"]
                basis, labels, names = read_basis(sid)
                test_x = basis[:, keep]
                if task != "baseline":
                    raw = np.load(CACHE_DIRS[task] / f"{sid}.npy", allow_pickle=False)
                    test_x = np.column_stack((test_x, average_rank01(raw).astype(np.float32)))
                loss = log_loss_bits(labels, model.predict_proba(test_x)[:, 1])
                item = {"series_id": sid, "source_dataset": source, "basis_variant": f"drop_{family}",
                        "condition": task, "n_points": len(labels), "n_anomalies": int(labels.sum())}
                if task == "baseline":
                    item["L_basis"] = loss
                else:
                    ref = reference.loc[sid]
                    item.update(L_basis=float(ref.L_basis), L_basis_detector=loss,
                                CDU=float(ref.L_basis) - loss)
                output.append(item)
            elapsed = time.perf_counter() - started
            atomic_csv(pd.DataFrame(output), path)
            atomic_json({"signature": signature, "test_source": source,
                         "training_sources": sorted({row['source'] for row in train}),
                         "runtime_seconds": elapsed, "warnings": [str(w.message) for w in caught],
                         "training_cap": cap, "test_points": "all", "dropped_family": family},
                        path.with_suffix(".json"))
            new_folds += 1
            print(f"[{family}/{task}] {number}/23 {source}: PASS runtime={elapsed:.1f}s", flush=True)
            del model, test_x, basis, labels
            gc.collect()
            if max_new_folds and new_folds >= max_new_folds:
                print(f"[{family}] pilot checkpoint saved", flush=True)
                return
        if task != "baseline":
            summarize(directory, sources, signature, task)
    atomic_json({"status": "COMPLETE", "signature": signature, "family": family},
                result_root / "QUEUE_STATUS.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--drop-family", required=True, choices=tuple(FAMILIES))
    parser.add_argument("--training-cap", type=int, default=2048)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--max-new-folds", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.training_cap <= 0:
        parser.error("basis sensitivity requires a positive accelerated training cap")
    with threadpool_limits(limits=args.threads):
        run(args.drop_family, args.training_cap, args.max_new_folds)


if __name__ == "__main__":
    main()
