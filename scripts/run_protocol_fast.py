"""Deadline-focused source-LOSO CDU evaluation with globally fixed C=0.1.

The script consumes frozen basis and detector score caches. It never runs a
detector. Every held-out source is an atomic, resumable checkpoint.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import time
import traceback
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from evaluate_cdu_protocol_v1 import (
    CACHE_DIRS,
    DETECTORS,
    EPS,
    SeriesRecord,
    average_rank01,
    cluster_bootstrap,
    feature_matrix,
    load_detector_records,
    load_source_map,
    log_loss_bits,
    make_probe,
    stack_training,
    weighted_training_prior,
)
from run_protocol_v1_controls import atomic_csv, atomic_json, load_basis_records


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "protocol_fast_results"
BASELINE = OUT / "shared_baseline"
VERSION = "CDU-protocol-fast-v1"
FIXED_C = 0.1
SEED = 2024


def duration(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def fixed_model(records: Sequence[SeriesRecord], condition: str):
    x, y, weights = stack_training(records, condition)
    model = make_probe(FIXED_C).fit(x, y, sample_weight=weights)
    del x, y, weights
    return model


def valid_checkpoint(csv_path: Path, json_path: Path, expected: int) -> bool:
    if not csv_path.is_file() or not json_path.is_file():
        return False
    try:
        frame = pd.read_csv(csv_path)
        metadata = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return bool(
        metadata.get("protocol_version") == VERSION
        and len(frame) == expected
        and frame["series_id"].nunique() == expected
        and np.isfinite(frame.select_dtypes(include=[np.number]).to_numpy()).all()
    )


def baseline_source(records: Sequence[SeriesRecord], held_source: str):
    train = [record for record in records if record.source_dataset != held_source]
    test = [record for record in records if record.source_dataset == held_source]
    model = fixed_model(train, "basis")
    prior = float(np.clip(weighted_training_prior(train), EPS, 1.0 - EPS))
    rows = []
    for record in test:
        l0 = log_loss_bits(record.y, np.full(len(record.y), prior))
        lb = log_loss_bits(record.y, model.predict_proba(record.basis)[:, 1])
        rows.append({
            "series_id": record.series_id,
            "source_dataset": held_source,
            "outer_fold": held_source,
            "L_null": l0,
            "L_basis": lb,
            "basis_utility": l0 - lb,
            "C_basis": FIXED_C,
            "n_points": len(record.y),
            "n_anomalies": int(np.sum(record.y)),
            "protocol_version": VERSION,
        })
    metadata = {
        "protocol_version": VERSION,
        "condition": "shared_baseline",
        "test_source_id": held_source,
        "training_source_ids": sorted({r.source_dataset for r in train}),
        "fixed_C": FIXED_C,
        "training_prior": prior,
        "n_test_series": len(test),
    }
    return pd.DataFrame(rows), metadata


def run_baseline() -> None:
    start = time.perf_counter()
    records, _ = load_basis_records()
    sources = sorted({record.source_dataset for record in records})
    runtimes: list[float] = []
    for position, source in enumerate(sources, 1):
        csv_path = BASELINE / "by_source" / f"{source}.csv"
        json_path = BASELINE / "by_source" / f"{source}.json"
        expected = sum(record.source_dataset == source for record in records)
        if valid_checkpoint(csv_path, json_path, expected):
            print(f"[baseline] outer {position}/23 {source}: SKIP", flush=True)
            continue
        tick = time.perf_counter()
        frame, metadata = baseline_source(records, source)
        atomic_csv(frame, csv_path)
        atomic_json(metadata, json_path)
        elapsed = time.perf_counter() - tick
        runtimes.append(elapsed)
        eta = np.mean(runtimes) * (23 - position)
        print(
            f"[baseline] outer {position}/23 {source}: PASS | "
            f"runtime={duration(elapsed)} ETA={duration(eta)}",
            flush=True,
        )
    combined = pd.concat(
        [pd.read_csv(BASELINE / "by_source" / f"{source}.csv") for source in sources],
        ignore_index=True,
    )
    if len(combined) != 350 or combined["series_id"].nunique() != 350:
        raise RuntimeError("Fast baseline does not cover 350 unique series")
    atomic_csv(combined, BASELINE / "PER_SERIES.csv")
    print(f"[baseline] COMPLETE 350/350 elapsed={duration(time.perf_counter()-start)}", flush=True)


def load_baseline() -> pd.DataFrame:
    path = BASELINE / "PER_SERIES.csv"
    if not path.is_file():
        raise RuntimeError("Fast shared baseline is missing; run with --baseline first")
    frame = pd.read_csv(path)
    if len(frame) != 350 or frame["series_id"].nunique() != 350:
        raise RuntimeError("Fast shared baseline is incomplete")
    return frame


def detector_source(
    records: Sequence[SeriesRecord], name: str, held_source: str, baseline: pd.DataFrame,
):
    train = [record for record in records if record.source_dataset != held_source]
    test = [record for record in records if record.source_dataset == held_source]
    detector_model = fixed_model(train, "detector")
    combined_model = fixed_model(train, "basis_detector")
    base = baseline.set_index("series_id")
    rows = []
    for record in test:
        reference = base.loc[record.series_id]
        ld = log_loss_bits(
            record.y,
            detector_model.predict_proba(record.detector_score[:, None])[:, 1],
        )
        lbd = log_loss_bits(
            record.y,
            combined_model.predict_proba(
                np.column_stack((record.basis, record.detector_score))
            )[:, 1],
        )
        l0 = float(reference.L_null)
        lb = float(reference.L_basis)
        rows.append({
            "series_id": record.series_id,
            "source_dataset": held_source,
            "detector": name,
            "outer_fold": held_source,
            "L_null": l0,
            "L_basis": lb,
            "L_detector": ld,
            "L_basis_detector": lbd,
            "basis_utility": l0 - lb,
            "detector_utility": l0 - ld,
            "basis_detector_utility": l0 - lbd,
            "CDU": lb - lbd,
            "C_basis": FIXED_C,
            "C_detector": FIXED_C,
            "C_basis_detector": FIXED_C,
            "n_points": len(record.y),
            "n_anomalies": int(np.sum(record.y)),
            "protocol_version": VERSION,
        })
    metadata = {
        "protocol_version": VERSION,
        "condition": name,
        "test_source_id": held_source,
        "training_source_ids": sorted({r.source_dataset for r in train}),
        "fixed_C": FIXED_C,
        "n_test_series": len(test),
    }
    return pd.DataFrame(rows), metadata


def aggregate(frame: pd.DataFrame):
    source = frame.groupby(["detector", "source_dataset"], as_index=False).agg(
        L_null=("L_null", "mean"),
        L_basis=("L_basis", "mean"),
        L_detector=("L_detector", "mean"),
        L_basis_detector=("L_basis_detector", "mean"),
        basis_utility=("basis_utility", "mean"),
        detector_utility=("detector_utility", "mean"),
        CDU=("CDU", "mean"),
        n_series=("series_id", "count"),
    )
    rows = []
    for detector, group in source.groupby("detector"):
        low, high, probability = cluster_bootstrap(group["CDU"])
        rows.append({
            "detector": detector,
            "L_null": group.L_null.mean(),
            "L_basis": group.L_basis.mean(),
            "L_detector": group.L_detector.mean(),
            "L_basis_detector": group.L_basis_detector.mean(),
            "basis_utility": group.basis_utility.mean(),
            "detector_utility": group.detector_utility.mean(),
            "CDU": group.CDU.mean(),
            "CDU_CI_low": low,
            "CDU_CI_high": high,
            "positive_source_fraction": float(np.mean(group.CDU > 0)),
            "bootstrap_prob_source_macro_positive": probability,
            "n_sources": len(group),
            "n_series": int(group.n_series.sum()),
            "fixed_C": FIXED_C,
            "protocol_version": VERSION,
        })
    return pd.DataFrame(rows), source


def run_records(name: str, records: Sequence[SeriesRecord]) -> None:
    start = time.perf_counter()
    baseline = load_baseline()
    sources = sorted({record.source_dataset for record in records})
    directory = OUT / "main" / name
    runtimes: list[float] = []
    for position, source in enumerate(sources, 1):
        csv_path = directory / "by_source" / f"{source}.csv"
        json_path = directory / "by_source" / f"{source}.json"
        expected = sum(record.source_dataset == source for record in records)
        if valid_checkpoint(csv_path, json_path, expected):
            print(f"[{name}] outer {position}/23 {source}: SKIP", flush=True)
            continue
        tick = time.perf_counter()
        frame, metadata = detector_source(records, name, source, baseline)
        atomic_csv(frame, csv_path)
        atomic_json(metadata, json_path)
        elapsed = time.perf_counter() - tick
        runtimes.append(elapsed)
        eta = np.mean(runtimes) * (23 - position)
        print(
            f"[{name}] outer {position}/23 {source}: PASS | "
            f"runtime={duration(elapsed)} ETA={duration(eta)}",
            flush=True,
        )
    combined = pd.concat(
        [pd.read_csv(directory / "by_source" / f"{source}.csv") for source in sources],
        ignore_index=True,
    )
    if len(combined) != 350 or combined["series_id"].nunique() != 350:
        raise RuntimeError(f"{name} does not cover 350 unique series")
    if not np.isfinite(combined.select_dtypes(include=[np.number]).to_numpy()).all():
        raise RuntimeError(f"{name} contains non-finite values")
    summary, per_source = aggregate(combined)
    atomic_csv(combined, directory / "PER_SERIES.csv")
    atomic_csv(per_source, directory / "PER_SOURCE.csv")
    atomic_csv(summary, directory / "SUMMARY.csv")
    print(f"[{name}] COMPLETE elapsed={duration(time.perf_counter()-start)}", flush=True)
    print(summary.to_string(index=False), flush=True)


def deterministic_noise(series_id: str, name: str, n: int) -> np.ndarray:
    key = f"{VERSION}|{series_id}|{name}".encode("utf-8")
    seed = int.from_bytes(hashlib.sha256(key).digest()[:8], "little")
    return np.random.default_rng(seed).standard_normal(n)


def control_records(kind: str) -> tuple[str, list[SeriesRecord]]:
    base, _ = load_basis_records()
    records = []
    for record in base:
        if kind == "duplicate":
            name = "duplicate_Var-96"
            score = record.basis[:, 4].copy()
        elif kind == "noise":
            name = "independent_noise"
            score = average_rank01(
                deterministic_noise(record.series_id, name, len(record.y))
            ).astype(np.float32)
        elif kind == "alpha2":
            name = "complementary_alpha_2"
            z = deterministic_noise(record.series_id, "complementary", len(record.y))
            score = average_rank01(z + 2.0 * record.y).astype(np.float32)
        else:
            raise ValueError(kind)
        records.append(SeriesRecord(
            series_id=record.series_id,
            source_dataset=record.source_dataset,
            y=record.y,
            basis=record.basis,
            detector_score=np.asarray(score, dtype=np.float32),
        ))
    return name, records


def dry_run(detectors: Sequence[str]) -> int:
    source_map = load_source_map()
    ok = True
    for detector in detectors:
        actual = {path.name for path in CACHE_DIRS[detector].glob("*.npy")}
        expected = {f"{series}.npy" for series in source_map}
        passed = actual == expected
        ok &= passed
        print(
            f"[{detector}] {'PASS' if passed else 'FAIL'} cache={len(actual)}/350 "
            f"missing={len(expected-actual)} extra={len(actual-expected)}",
            flush=True,
        )
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--detectors", nargs="+", choices=DETECTORS)
    parser.add_argument("--controls", nargs="+", choices=("duplicate", "noise", "alpha2"))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.baseline and not args.detectors and not args.controls:
        parser.error("select --baseline, --detectors, and/or --controls")
    detectors = list(dict.fromkeys(args.detectors or []))
    if args.dry_run:
        return dry_run(detectors)

    failures = {}
    if args.baseline:
        run_baseline()
    for detector in detectors:
        try:
            run_records(detector, load_detector_records(detector))
        except Exception as error:
            failures[detector] = f"{type(error).__name__}: {error}"
            traceback.print_exc()
            if not args.continue_on_error:
                break
        finally:
            gc.collect()
    for control in args.controls or []:
        try:
            name, records = control_records(control)
            run_records(name, records)
        except Exception as error:
            failures[control] = f"{type(error).__name__}: {error}"
            traceback.print_exc()
            if not args.continue_on_error:
                break
        finally:
            gc.collect()
    atomic_json({
        "protocol_version": VERSION,
        "fixed_C": FIXED_C,
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }, OUT / "QUEUE_STATUS.json")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
