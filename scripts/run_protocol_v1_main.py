"""Resumable Protocol-v1 main evaluation over frozen detector score caches.

This runner never executes a detector.  It reuses the completed shared L0/LB
baseline and computes only detector-only (LD) and basis-plus-detector (LBD)
models.  Results are checkpointed independently for every held-out source.
"""
from __future__ import annotations

import argparse
import gc
import json
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

from evaluate_cdu_protocol_v1 import (
    CACHE_DIRS,
    DETECTORS,
    PROTOCOL_VERSION,
    aggregate_complete,
    load_detector_records,
    load_source_map,
)
from run_protocol_v1_controls import (
    BASELINE,
    atomic_csv,
    atomic_json,
    compute_control_source,
    enforce_signature,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "protocol_v1_results" / "main"


def format_duration(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def load_shared_baseline() -> pd.DataFrame:
    path = BASELINE / "BASELINE_PER_SERIES.csv"
    if not path.is_file():
        raise RuntimeError(f"Shared baseline is missing: {path}")
    frame = pd.read_csv(path)
    if len(frame) != 350 or frame["series_id"].nunique() != 350:
        raise RuntimeError("Shared baseline must contain exactly 350 unique series")
    required = {"series_id", "source_dataset", "L_null", "L_basis", "C_basis"}
    missing = required.difference(frame.columns)
    if missing:
        raise RuntimeError(f"Shared baseline columns missing: {sorted(missing)}")
    if not np.isfinite(frame[["L_null", "L_basis", "C_basis"]].to_numpy(float)).all():
        raise RuntimeError("Shared baseline contains non-finite values")
    return frame


def checkpoint_valid(
    csv_path: Path,
    json_path: Path,
    protocol_signature: str,
    expected_series: int,
) -> bool:
    if not csv_path.is_file() or not json_path.is_file():
        return False
    try:
        metadata = json.loads(json_path.read_text(encoding="utf-8"))
        signature = metadata.get("protocol_signature", metadata.get("run_signature"))
        frame = pd.read_csv(csv_path)
    except Exception:
        return False
    return bool(
        signature == protocol_signature
        and len(frame) == expected_series
        and frame["series_id"].nunique() == expected_series
        and np.isfinite(frame.select_dtypes(include=[np.number]).to_numpy()).all()
    )


def validate_baseline_identity(result: pd.DataFrame, baseline: pd.DataFrame) -> None:
    columns = ["series_id", "L_null", "L_basis"]
    observed = result[columns].sort_values("series_id").reset_index(drop=True)
    expected = baseline[columns].sort_values("series_id").reset_index(drop=True)
    if not observed["series_id"].equals(expected["series_id"]):
        raise RuntimeError("Main result series do not match the shared baseline")
    for column in ("L_null", "L_basis"):
        if not np.array_equal(observed[column].to_numpy(), expected[column].to_numpy()):
            raise RuntimeError(f"Shared baseline identity failure for {column}")


def dry_run(detectors: list[str]) -> int:
    source_map = load_source_map()
    baseline = load_shared_baseline()
    ok = True
    for detector in detectors:
        cache = CACHE_DIRS[detector]
        expected = {f"{series_id}.npy" for series_id in source_map}
        actual = {path.name for path in cache.glob("*.npy")} if cache.is_dir() else set()
        missing = expected.difference(actual)
        extra = actual.difference(expected)
        passed = not missing and not extra
        ok &= passed
        print(
            f"[{detector}] {'PASS' if passed else 'FAIL'} cache={len(actual)}/350 "
            f"missing={len(missing)} extra={len(extra)}",
            flush=True,
        )
    print(
        f"shared baseline: {len(baseline)}/350; sources={baseline.source_dataset.nunique()}",
        flush=True,
    )
    return 0 if ok else 1


def run_detector(detector: str, protocol_signature: str) -> None:
    detector_start = time.perf_counter()
    baseline = load_shared_baseline()
    records = load_detector_records(detector)
    sources = sorted({record.source_dataset for record in records})
    if len(sources) != 23:
        raise RuntimeError(f"Expected 23 sources, found {len(sources)}")

    directory = OUT / detector
    by_source = directory / "by_source"
    runtimes: list[float] = []
    passed = 0
    skipped = 0

    for position, source in enumerate(sources, 1):
        csv_path = by_source / f"{source}.csv"
        json_path = by_source / f"{source}.json"
        expected_series = sum(record.source_dataset == source for record in records)
        if checkpoint_valid(
            csv_path, json_path, protocol_signature, expected_series
        ):
            skipped += 1
            print(
                f"[{detector}] outer {position}/23 {source}: SKIP | "
                f"PASS={passed} SKIP={skipped}",
                flush=True,
            )
            continue

        source_start = time.perf_counter()
        frame, metadata = compute_control_source(records, detector, source, baseline)
        metadata["protocol_signature"] = protocol_signature
        metadata["run_signature"] = protocol_signature  # Backward-compatible field.
        metadata["experiment"] = {"type": "detector", "detector": detector}
        atomic_csv(frame, csv_path)
        atomic_json(metadata, json_path)
        runtime = time.perf_counter() - source_start
        runtimes.append(runtime)
        passed += 1
        remaining = 23 - position
        eta = float(np.mean(runtimes) * remaining) if runtimes else 0.0
        print(
            f"[{detector}] outer {position}/23 {source}: PASS "
            f"({len(frame)} series) | runtime={format_duration(runtime)} | "
            f"PASS={passed} SKIP={skipped} | ETA={format_duration(eta)}",
            flush=True,
        )

    pieces = [pd.read_csv(by_source / f"{source}.csv") for source in sources]
    combined = pd.concat(pieces, ignore_index=True)
    if len(combined) != 350 or combined["series_id"].nunique() != 350:
        raise RuntimeError("Main output must contain exactly 350 unique series")
    if not np.isfinite(combined.select_dtypes(include=[np.number]).to_numpy()).all():
        raise RuntimeError("Main output contains non-finite values")
    validate_baseline_identity(combined, baseline)

    summary, per_source = aggregate_complete(combined)
    atomic_csv(combined, directory / "PER_SERIES.csv")
    atomic_csv(per_source, directory / "PER_SOURCE.csv")
    atomic_csv(summary, directory / "SUMMARY.csv")
    print(
        f"[{detector}] COMPLETE 350/350 | elapsed="
        f"{format_duration(time.perf_counter() - detector_start)}",
        flush=True,
    )
    print(summary.to_string(index=False), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--detectors", nargs="+", choices=DETECTORS, required=True,
        help="One or more frozen detectors, run sequentially in the given order.",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Accepted for an explicit resumable command; valid source checkpoints are always skipped.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--continue-on-error", action="store_true",
        help="Attempt later detectors if an earlier detector fails.",
    )
    args = parser.parse_args()
    detectors = list(dict.fromkeys(args.detectors))
    if args.dry_run:
        return dry_run(detectors)

    signature = enforce_signature()["run_signature"]
    print(f"Protocol: {PROTOCOL_VERSION}", flush=True)
    print(f"Protocol signature: {signature}", flush=True)
    print(f"Detector queue: {', '.join(detectors)}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    failures: dict[str, str] = {}
    for detector in detectors:
        try:
            run_detector(detector, signature)
        except Exception as error:
            failures[detector] = f"{type(error).__name__}: {error}"
            print(f"[{detector}] FAIL: {failures[detector]}", flush=True)
            traceback.print_exc()
            if not args.continue_on_error:
                break
        finally:
            gc.collect()

    status_path = OUT / "QUEUE_STATUS.json"
    atomic_json(
        {
            "protocol_version": PROTOCOL_VERSION,
            "protocol_signature": signature,
            "requested_detectors": detectors,
            "failures": failures,
            "status": "PASS" if not failures else "FAIL",
        },
        status_path,
    )
    if failures:
        print(f"QUEUE COMPLETE WITH FAILURES: {failures}", flush=True)
        return 1
    print("MAIN DETECTOR QUEUE COMPLETE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
