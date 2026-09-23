"""Offline reference-interface robustness for the frozen nine detector scores.

Two experiments are supported:

``normalization``
    Keep the ranked 31-feature statistical reference fixed and replace only the
    label-free, within-series detector-score interface.  The primary rank
    setting already exists; this runner adds min-max and Gaussianized z-score
    interfaces under the same spline probe.

``strength``
    Keep the ranked detector-score interface fixed and grow the statistical
    reference through four predeclared cumulative feature sets.  The full
    31-feature setting already exists and is used by the paper's primary run.

The runner never executes a detector.  Every source fold is checkpointed, so
``--resume`` is safe after interruption.  Test curves always remain complete.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import ndtr
from threadpoolctl import threadpool_limits

from evaluate_cdu_protocol_v1 import CACHE_DIRS, DETECTORS, average_rank01, load_source_map, log_loss_bits
from run_basis_sensitivity import checkpoint, summarize
from run_probe_robustness import sample_indices, weights
from run_protocol_v1_controls import atomic_csv, atomic_json
from run_rank_probe_extension import Probe
from run_symmetric_rank import RANKED, read_ranked_basis


ROOT = Path(__file__).resolve().parents[1]
PRIMARY = ROOT / "protocol_rank_probe_results" / "cap2048" / "spline"
OUT = ROOT / "protocol_reference_robustness"
VERSION = "reference-robustness-v1"
SAMPLE_VERSION = "rank-probe-matched-v1"  # identical sampled rows to the primary run

NORMALIZATIONS = ("minmax", "zscore_cdf")
STRENGTHS = {
    "variance": ("Var-",),
    "variance_range": ("Var-", "Range-"),
    "local_deviation": ("Var-", "Range-", "Last-", "Centered-"),
    "dispersion_change": ("Var-", "Range-", "Last-", "Centered-", "AbsDiff-", "MAD-"),
}


def detector_transform(raw: np.ndarray, variant: str) -> np.ndarray:
    x = np.asarray(raw, dtype=float).reshape(-1)
    if not np.isfinite(x).all() or not len(x):
        raise RuntimeError("Detector score is empty or non-finite")
    if variant == "rank":
        return average_rank01(x).astype(np.float32)
    span = float(np.ptp(x))
    if span == 0:
        return np.full(len(x), 0.5, dtype=np.float32)
    if variant == "minmax":
        return ((x - np.min(x)) / span).astype(np.float32)
    if variant == "zscore_cdf":
        sd = float(np.std(x))
        if sd == 0:
            return np.full(len(x), 0.5, dtype=np.float32)
        return ndtr((x - np.mean(x)) / sd).astype(np.float32)
    raise ValueError(variant)


def strength_mask(names: tuple[str, ...], variant: str) -> np.ndarray:
    prefixes = STRENGTHS[variant]
    keep = np.asarray([any(name.startswith(prefix) for prefix in prefixes) for name in names])
    if not keep.any() or keep.all():
        raise RuntimeError(f"Invalid strength definition {variant}: {keep.sum()}/{len(keep)}")
    return keep


def read_primary_baseline(source: str, expected: set[str]) -> pd.DataFrame:
    path = PRIMARY / "baseline" / "by_source" / f"{source}.csv"
    frame = pd.read_csv(path)
    if not frame.series_id.is_unique or set(frame.series_id) != expected:
        raise RuntimeError(f"Primary baseline population mismatch: {source}")
    if not np.isfinite(frame.select_dtypes(include=[np.number]).to_numpy()).all():
        raise RuntimeError(f"Non-finite primary baseline: {source}")
    return frame.set_index("series_id")


def score(sid: str, detector: str, n: int, transform: str) -> np.ndarray:
    raw = np.load(CACHE_DIRS[detector] / f"{sid}.npy", allow_pickle=False).reshape(-1)
    if raw.shape != (n,):
        raise RuntimeError(f"Score length mismatch {detector}/{sid}: {len(raw)} != {n}")
    return detector_transform(raw, transform)


def prepare(cap: int, experiment: str, variant: str):
    mapping = load_source_map()
    ids = sorted(mapping)
    arrays, labels, rows, cursor = [], [], [], 0
    names0 = None
    keep = None
    for ordinal, sid in enumerate(ids, 1):
        basis, y, names = read_ranked_basis(sid)
        if names0 is None:
            names0 = names
            keep = (np.ones(len(names), dtype=bool) if experiment == "normalization"
                    else strength_mask(names, variant))
        elif names != names0:
            raise RuntimeError(f"Basis name/order drift: {sid}")
        idx = sample_indices(sid, len(y), cap, SAMPLE_VERSION)
        arrays.append(basis[idx][:, keep])
        labels.append(y[idx])
        rows.append({"series_id": sid, "source": mapping[sid], "start": cursor,
                     "end": cursor + len(idx), "n_full": len(y)})
        cursor += len(idx)
        if ordinal % 50 == 0:
            print(f"[{experiment}/{variant}/prepare] {ordinal}/350 p={int(keep.sum())}", flush=True)
    return mapping, rows, np.concatenate(arrays), np.concatenate(labels), keep


def run(experiment: str, variant: str, cap: int, max_new_folds: int):
    mapping, rows, xall, yall, keep = prepare(cap, experiment, variant)
    sources = sorted(set(mapping.values()))
    folder = OUT / experiment / f"cap{cap}" / variant
    config = {
        "version": VERSION,
        "experiment": experiment,
        "variant": variant,
        "training_cap": cap,
        "probe": "additive cubic-spline logistic",
        "C": 0.1,
        "sample_version": SAMPLE_VERSION,
        "test_points": "all",
        "aggregation": "source macro of series mean loss",
        "basis_columns": int(keep.sum()),
        "source_map_sha256": hashlib.sha256((ROOT / "source_groups.json").read_bytes()).hexdigest(),
        "ranked_basis_manifest_sha256": hashlib.sha256((RANKED / "MANIFEST.json").read_bytes()).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "primary_baseline": str(PRIMARY / "baseline") if experiment == "normalization" else None,
    }
    signature = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    manifest = folder / "RUN_MANIFEST.json"
    if manifest.exists() and json.loads(manifest.read_text()).get("signature") != signature:
        raise RuntimeError(f"Existing result identity differs: {folder}")
    atomic_json({"config": config, "signature": signature}, manifest)

    tasks = list(DETECTORS) if experiment == "normalization" else ["baseline", *DETECTORS]
    fitted = 0
    for task in tasks:
        directory = folder / task
        if task != "baseline" and (directory / "SUMMARY.csv").exists():
            print(f"[{experiment}/{variant}/{task}] COMPLETE: SKIP", flush=True)
            continue
        for number, source in enumerate(sources, 1):
            target = directory / "by_source" / f"{source}.csv"
            test = [row for row in rows if row["source"] == source]
            train = [row for row in rows if row["source"] != source]
            expected = {row["series_id"] for row in test}
            if checkpoint(target, signature, expected) is not None:
                print(f"[{experiment}/{variant}/{task}] {number}/23 {source}: SKIP", flush=True)
                continue
            started = time.perf_counter()
            x = np.concatenate([xall[row["start"]:row["end"]] for row in train])
            y = np.concatenate([yall[row["start"]:row["end"]] for row in train])
            if task != "baseline":
                transform = variant if experiment == "normalization" else "rank"
                curves = []
                for row in train:
                    curve = score(row["series_id"], task, row["n_full"], transform)
                    idx = sample_indices(row["series_id"], len(curve), cap, SAMPLE_VERSION)
                    curves.append(curve[idx])
                x = np.column_stack([x, np.concatenate(curves)])
            print(f"[{experiment}/{variant}/{task}] {number}/23 {source}: FIT n={len(y)} p={x.shape[1]}", flush=True)
            model = Probe("spline").fit(x, y, weights(train))
            reference = (read_primary_baseline(source, expected) if experiment == "normalization"
                         else None)
            if task != "baseline" and experiment == "strength":
                reference = checkpoint(folder / "baseline" / "by_source" / f"{source}.csv",
                                       signature, expected).set_index("series_id")
            output = []
            for row in test:
                sid = row["series_id"]
                basis, labels, _ = read_ranked_basis(sid)
                test_x = basis[:, keep]
                if task != "baseline":
                    transform = variant if experiment == "normalization" else "rank"
                    test_x = np.column_stack([test_x, score(sid, task, len(labels), transform)])
                loss = log_loss_bits(labels, model.predict_proba(test_x)[:, 1])
                item = {"series_id": sid, "source_dataset": source, "condition": task,
                        "experiment": experiment, "variant": variant,
                        "n_points": len(labels), "n_anomalies": int(labels.sum())}
                if task == "baseline":
                    item["L_basis"] = loss
                else:
                    lb = float(reference.loc[sid].L_basis)
                    item.update(L_basis=lb, L_basis_detector=loss, CDU=lb - loss)
                output.append(item)
            elapsed = time.perf_counter() - started
            atomic_csv(pd.DataFrame(output), target)
            atomic_json({"signature": signature, "runtime_seconds": elapsed,
                         "test_source": source,
                         "training_sources": sorted({row["source"] for row in train})},
                        target.with_suffix(".json"))
            print(f"[{experiment}/{variant}/{task}] {number}/23 {source}: PASS runtime={elapsed:.1f}s", flush=True)
            fitted += 1
            if max_new_folds and fitted >= max_new_folds:
                return
        if task == "baseline":
            atomic_csv(pd.concat([pd.read_csv(directory / "by_source" / f"{s}.csv") for s in sources]),
                       directory / "PER_SERIES.csv")
        else:
            summarize(directory, sources, signature, task)
    atomic_json({"status": "COMPLETE", "signature": signature}, folder / "QUEUE_STATUS.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", choices=("normalization", "strength"), required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--training-cap", type=int, default=2048)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--max-new-folds", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    allowed = NORMALIZATIONS if args.experiment == "normalization" else tuple(STRENGTHS)
    if args.variant not in allowed:
        parser.error(f"--variant must be one of {allowed} for {args.experiment}")
    with threadpool_limits(limits=args.threads):
        run(args.experiment, args.variant, args.training_cap, args.max_new_folds)


if __name__ == "__main__":
    main()
