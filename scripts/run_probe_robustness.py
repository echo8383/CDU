"""Independent fixed-probe sensitivity on frozen caches, with resumable source folds.

No detector training, altered basis features, point drops at evaluation, or tuning.
The approved configuration uses bounded training and runs matched logistic as
well as HGB on identical sampled indices. All test timestamps remain untouched.
"""
from __future__ import annotations
import argparse
import gc
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
import time
import traceback
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits

from evaluate_cdu_protocol_v1 import (
    CACHE_DIRS, DETECTORS, average_rank01, log_loss_bits, make_probe, load_source_map,
)
from run_protocol_fast import deterministic_noise
from run_protocol_v1_controls import atomic_csv, atomic_json

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/probe_robustness_hgb.json"
CONTROL_NAMES = {"duplicate": "duplicate_Var-96", "noise": "independent_noise",
                 "alpha2": "complementary_alpha_2"}


def sample_indices(sid, length, cap, version):
    if not cap or length <= cap:
        return np.arange(length)
    seed = int.from_bytes(hashlib.sha256(f"{version}|{sid}".encode()).digest()[:8], "little")
    return np.sort(np.random.default_rng(seed).choice(length, size=cap, replace=False))


def read_basis(sid):
    with np.load(ROOT / "layer2_results/basis_scores" / (sid + ".npz"), allow_pickle=False) as payload:
        basis = payload["basis"]
        labels = payload["label"].astype(np.int8)
        names = tuple(map(str, payload["names"]))
    if basis.shape[0] == 31:
        basis = basis.T
    if basis.shape != (len(labels), 31) or not np.isfinite(basis).all():
        raise RuntimeError(f"Invalid basis: {sid}")
    if not np.isin(labels, [0, 1]).all():
        raise RuntimeError(f"Invalid labels: {sid}")
    return np.asarray(basis, dtype=np.float32), labels, names


def load_score(sid, name, basis, labels):
    if name == "duplicate":
        return basis[:, 4].copy()
    if name == "noise":
        raw = deterministic_noise(sid, "independent_noise", len(labels))
    elif name == "alpha2":
        raw = deterministic_noise(sid, "complementary", len(labels)) + 2 * labels
    else:
        raw = np.load(CACHE_DIRS[name] / (sid + ".npy"), allow_pickle=False)
    if raw.ndim != 1 or len(raw) != len(labels) or not np.isfinite(raw).all():
        raise RuntimeError(f"Invalid score: {name}/{sid}")
    return average_rank01(raw).astype(np.float32)


def make_model(probe, config):
    if probe == "logistic":
        return make_probe(.1)
    return HistGradientBoostingClassifier(**config["hgb"])


def weights(rows):
    counts = {}
    for row in rows:
        counts[row["source"]] = counts.get(row["source"], 0) + 1
    n = sum(row["end"] - row["start"] for row in rows)
    return np.concatenate([np.full(row["end"]-row["start"],
        n / (len(counts) * counts[row["source"]] * (row["end"]-row["start"])), dtype=float)
        for row in rows])


def checkpoint(path, signature, expected):
    meta = path.with_suffix(".json")
    if not path.exists() or not meta.exists():
        return None
    metadata = json.loads(meta.read_text())
    if metadata["signature"] != signature:
        raise RuntimeError("Checkpoint identity changed; refusing mixed robustness versions")
    frame = pd.read_csv(path)
    if not frame.series_id.is_unique or set(frame.series_id) != expected:
        raise RuntimeError(f"Invalid checkpoint population: {path}")
    if not np.isfinite(frame.select_dtypes(include=[np.number]).to_numpy()).all():
        raise RuntimeError(f"Non-finite checkpoint: {path}")
    return frame


def summarize(directory, sources, signature, name, probe):
    if not all((directory / "by_source" / (s + ".csv")).exists() for s in sources):
        return
    frame = pd.concat([pd.read_csv(directory / "by_source" / (s + ".csv")) for s in sources])
    assert len(frame) == 350 and frame.series_id.nunique() == 350
    atomic_csv(frame, directory / "PER_SERIES.csv")
    if name == "baseline":
        return
    np.testing.assert_allclose(frame.CDU, frame.L_basis - frame.L_basis_detector, atol=1e-14)
    source = frame.groupby("source_dataset", as_index=False).agg(
        L_basis=("L_basis", "mean"), L_basis_detector=("L_basis_detector", "mean"),
        CDU=("CDU", "mean"), n_series=("series_id", "count"))
    v = source.CDU.to_numpy()
    boot = v[np.random.default_rng(2024).integers(0, 23, size=(10000, 23))].mean(axis=1)
    lo, hi = np.quantile(boot, [.025, .975])
    summary = {"detector": CONTROL_NAMES.get(name, name), "probe": probe, "CDU": v.mean(),
        "CDU_CI_low": lo, "CDU_CI_high": hi, "positive_sources": int((v > 0).sum()),
        "bootstrap_prob_source_macro_positive": float((boot > 0).mean()),
        "n_series": 350, "n_sources": 23, "signature": signature}
    atomic_csv(source, directory / "PER_SOURCE.csv")
    atomic_csv(pd.DataFrame([summary]), directory / "SUMMARY.csv")
    print(f"[{probe}/{name}] COMPLETE {summary}", flush=True)


def run(config, args):
    mapping = load_source_map()
    ids, sources = sorted(mapping), sorted(set(mapping.values()))
    config["training_cap_per_series"] = args.training_cap
    probes = ["hgb"] if not args.training_cap else ["logistic", "hgb"]
    folder = ROOT / "protocol_probe_results" / ("full" if not args.training_cap else f"cap{args.training_cap}")
    signature_payload = {
        "config": config, "probes": probes,
        "runner_hash": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_map_hash": hashlib.sha256((ROOT / "source_groups.json").read_bytes()).hexdigest(),
        "basis_manifest_hash": hashlib.sha256((ROOT / "protocol_v1_input_manifest.json").read_bytes()).hexdigest(),
        "feature_code_hash": hashlib.sha256((ROOT / "scripts/evaluate_cdu_protocol_v1.py").read_bytes()).hexdigest(),
        "control_code_hash": hashlib.sha256((ROOT / "scripts/run_protocol_fast.py").read_bytes()).hexdigest(),
    }
    # Stat identities detect replaced caches without allocating/rehashing all curves.
    # Basis and score arrays are checked when actually read below.
    input_paths = [ROOT / "layer2_results/basis_scores" / (sid + ".npz") for sid in ids]
    input_paths += [CACHE_DIRS[d] / (sid + ".npy") for d in DETECTORS for sid in ids]
    signature_payload["input_identity"] = [
        [p.relative_to(ROOT).as_posix(), p.stat().st_size, p.stat().st_mtime_ns] for p in input_paths]
    signature = hashlib.sha256(json.dumps(signature_payload, sort_keys=True).encode()).hexdigest()
    manifest_path = folder / "RUN_MANIFEST.json"
    if manifest_path.exists():
        if json.loads(manifest_path.read_text())["signature"] != signature:
            raise RuntimeError("Config/code/cache identity changed; use a separate result version")
    else:
        atomic_json({**signature_payload, "signature": signature}, manifest_path)

    # Prepare training data only once. Full test curves remain untouched and are
    # loaded one series at a time to avoid multiplying the 2.25 GB basis cache.
    lengths = pd.read_csv(ROOT / "protocol_fast_results/shared_baseline/PER_SERIES.csv").set_index("series_id").n_points
    total = sum(min(int(lengths[sid]), args.training_cap) if args.training_cap else int(lengths[sid]) for sid in ids)
    basis_train = np.empty((total, 31), np.float32)
    y_train = np.empty(total, np.int8)
    rows, cursor, expected_names = [], 0, None
    for ordinal, sid in enumerate(ids, 1):
        b, y, names = read_basis(sid)
        if expected_names is None:
            expected_names = names
            assert len(names) == 31 and names[4] == "Var-96"
        assert names == expected_names and len(y) == int(lengths[sid])
        idx = sample_indices(sid, len(y), args.training_cap, config["version"])
        end = cursor + len(idx)
        basis_train[cursor:end], y_train[cursor:end] = b[idx], y[idx]
        rows.append({"series_id": sid, "source": mapping[sid], "start": cursor, "end": end,
                     "n_full": len(y)})
        cursor = end
        if ordinal % 50 == 0:
            print(f"[prepare] {ordinal}/350 training_points={cursor}", flush=True)
    del b, y, idx
    gc.collect()

    # Baselines for each probe are computed once, then reused by every condition.
    tasks = ["baseline", "duplicate", "noise", "alpha2"] + list(DETECTORS)
    if args.tasks:
        tasks = ["baseline"] + [t for t in args.tasks if t != "baseline"]
    failures = {}
    fits = 0
    for task in tasks:
        scores = None
        # Skip disk loading for fully completed conditions.
        if all((folder / p / CONTROL_NAMES.get(task, task) / "SUMMARY.csv").exists() for p in probes):
            print(f"[{task}] completed summaries present: SKIP", flush=True)
            continue
        if task != "baseline":
            scores = np.empty(total, np.float32)
            for row in rows:
                b, y, _ = read_basis(row["series_id"])
                s = load_score(row["series_id"], task, b, y)
                idx = sample_indices(row["series_id"], len(y), args.training_cap, config["version"])
                scores[row["start"]:row["end"]] = s[idx]
            del b, y, s, idx
        for probe in probes:
            directory = folder / probe / CONTROL_NAMES.get(task, task)
            try:
                for number, source in enumerate(sources, 1):
                    path = directory / "by_source" / (source + ".csv")
                    test_rows = [r for r in rows if r["source"] == source]
                    expected = {r["series_id"] for r in test_rows}
                    if checkpoint(path, signature, expected) is not None:
                        print(f"[{probe}/{task}] {number}/23 {source}: SKIP", flush=True)
                        continue
                    train = [r for r in rows if r["source"] != source]
                    assert set(r["source"] for r in train) == set(sources) - {source}
                    start = time.perf_counter()
                    x = np.concatenate([basis_train[r["start"]:r["end"]] for r in train])
                    if task != "baseline":
                        score = np.concatenate([scores[r["start"]:r["end"]] for r in train])
                        x = np.column_stack([x, score])
                        del score
                    labels = np.concatenate([y_train[r["start"]:r["end"]] for r in train])
                    w = weights(train)
                    assert len(x) == len(labels) == len(w)
                    assert np.isclose(w.sum(), len(w))
                    print(f"[{probe}/{task}] {number}/23 {source}: FIT n={len(x)} p={x.shape[1]}", flush=True)
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter("always", ConvergenceWarning)
                        model = make_model(probe, config).fit(x, labels, sample_weight=w)
                    warning_text = [str(item.message) for item in caught]
                    del x, labels, w
                    gc.collect()
                    baseline = None
                    if task != "baseline":
                        bp = folder / probe / "baseline/by_source" / (source + ".csv")
                        baseline = checkpoint(bp, signature, expected)
                        if baseline is None:
                            raise RuntimeError("Matching probe baseline is missing")
                        baseline = baseline.set_index("series_id")
                    output = []
                    for row in test_rows:
                        sid = row["series_id"]
                        b, y, _ = read_basis(sid)
                        if task != "baseline":
                            s = load_score(sid, task, b, y)
                            b = np.column_stack([b, s])
                        loss = log_loss_bits(y, model.predict_proba(b)[:, 1])
                        item = {"series_id": sid, "source_dataset": source, "probe": probe,
                                "condition": task, "n_points": len(y), "n_anomalies": int(y.sum())}
                        if task == "baseline":
                            item["L_basis"] = loss
                        else:
                            ref = baseline.loc[sid]
                            assert ref.n_points == len(y) and ref.n_anomalies == y.sum()
                            item.update(L_basis=float(ref.L_basis), L_basis_detector=loss,
                                        CDU=float(ref.L_basis)-loss)
                        output.append(item)
                    elapsed = time.perf_counter() - start
                    atomic_csv(pd.DataFrame(output), path)
                    atomic_json({"signature": signature, "test_source": source,
                        "training_sources": sorted(set(r["source"] for r in train)),
                        "runtime_seconds": elapsed, "warnings": warning_text,
                        "training_cap": args.training_cap, "test_points": "all"}, path.with_suffix(".json"))
                    del model, b, y
                    gc.collect()
                    fits += 1
                    print(f"[{probe}/{task}] {number}/23 {source}: PASS runtime={elapsed:.1f}s warnings={warning_text}", flush=True)
                    if args.max_new_folds and fits >= args.max_new_folds:
                        print("[pilot] requested number of new fits completed; checkpoint saved.", flush=True)
                        return
                summarize(directory, sources, signature, task, probe)
                if task != "baseline":
                    subprocess.run([sys.executable, str(ROOT / "scripts/summarize_probe_robustness.py"),
                                    "--training-cap", str(args.training_cap)], check=True)
            except Exception as error:
                failures[f"{probe}/{task}"] = str(error)
                traceback.print_exc()
                if task == "baseline":
                    raise
            gc.collect()
    atomic_json({"failures": failures, "signature": signature,
                 "status": "FAIL" if failures else "COMPLETE"}, folder / "QUEUE_STATUS.json")
    if failures:
        raise RuntimeError(f"Robustness conditions failed: {failures}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--training-cap", type=int, default=None)
    parser.add_argument("--max-new-folds", type=int, default=0)
    parser.add_argument("--tasks", nargs="+", choices=["baseline", "duplicate", "noise", "alpha2"] + list(DETECTORS))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text())
    if args.training_cap is None:
        args.training_cap = config["training_cap_per_series"]
    if args.training_cap < 0:
        parser.error("training cap cannot be negative")
    with threadpool_limits(limits=config["threads"]):
        run(config, args)


if __name__ == "__main__":
    main()
