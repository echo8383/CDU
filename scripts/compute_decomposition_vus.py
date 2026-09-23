"""Compute frozen VUS-PR for reconstructed and residual score caches."""
from __future__ import annotations

import argparse
import hashlib
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, r"D:\CSIES\AI4Energy\others\TSB-AD")
from vus_eval.basic_metrics import generate_curve

from evaluate_cdu_protocol_v1 import DETECTORS, load_source_map
from run_protocol_v1_controls import atomic_csv
from run_symmetric_rank import read_ranked_basis

DECOMP = ROOT / "protocol_score_decomposition/cap2048"
OUT = DECOMP / "vus"


def metric(label, score, window):
    if len(label) != len(score) or not np.isfinite(score).all():
        raise RuntimeError("Invalid VUS inputs")
    return 0.0 if np.ptp(score) == 0 else float(generate_curve(label, score, int(window), "opt", 250)[7])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--detector", required=True, choices=DETECTORS)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    detector = args.detector
    mapping = load_source_map()
    ids = sorted(mapping)
    windows = (pd.read_csv(ROOT / "layer2_results/audit_raw_vus_per_series.csv")
               .drop_duplicates("series_id").set_index("series_id").window_from_raw_data)
    output_path = OUT / f"{detector}.csv"
    rows = []
    if args.resume and output_path.exists():
        rows = pd.read_csv(output_path).to_dict("records")
    done = {str(row["series_id"]) for row in rows if row.get("status") == "PASS"}
    rows = [row for row in rows if str(row["series_id"]) in done]
    started = time.perf_counter()
    for ordinal, sid in enumerate(ids, 1):
        if sid in done:
            print(f"[{detector}/VUS] {ordinal}/350 {sid}: SKIP", flush=True)
            continue
        item_started = time.perf_counter()
        try:
            _, label, _ = read_ranked_basis(sid)
            predicted = np.load(DECOMP / "predicted" / detector / f"{sid}.npy", allow_pickle=False)
            residual = np.load(DECOMP / "residual" / detector / f"{sid}.npy", allow_pickle=False)
            row = {"detector": detector, "series_id": sid, "source_dataset": mapping[sid],
                   "n_points": len(label), "window": int(windows.loc[sid]),
                   "predicted_VUS_PR": metric(label, predicted, windows.loc[sid]),
                   "residual_VUS_PR": metric(label, residual, windows.loc[sid]),
                   "predicted_hash": hashlib.sha256(np.ascontiguousarray(predicted).tobytes()).hexdigest(),
                   "residual_hash": hashlib.sha256(np.ascontiguousarray(residual).tobytes()).hexdigest(),
                   "status": "PASS", "error": ""}
        except Exception as error:
            row = {"detector": detector, "series_id": sid, "source_dataset": mapping[sid],
                   "status": "FAIL", "error": repr(error)}
        rows.append(row)
        atomic_csv(pd.DataFrame(rows).drop_duplicates("series_id", keep="last"), output_path)
        elapsed = time.perf_counter() - started
        remaining = len(ids) - ordinal
        eta = remaining * elapsed / max(ordinal - len(done), 1)
        print(f"[{detector}/VUS] {ordinal}/350 {sid}: {row['status']} "
              f"runtime={time.perf_counter()-item_started:.1f}s ETA={eta/60:.1f}m", flush=True)
    frame = pd.DataFrame(rows).drop_duplicates("series_id", keep="last")
    atomic_csv(frame, output_path)
    good = frame[frame.status == "PASS"]
    source = good.groupby("source_dataset")[["predicted_VUS_PR", "residual_VUS_PR"]].mean()
    summary = pd.DataFrame([{"detector": detector, "n_series": len(good),
        "predicted_VUS_series_macro": good.predicted_VUS_PR.mean(),
        "residual_VUS_series_macro": good.residual_VUS_PR.mean(),
        "predicted_VUS_source_macro": source.predicted_VUS_PR.mean(),
        "residual_VUS_source_macro": source.residual_VUS_PR.mean()}])
    atomic_csv(summary, OUT / f"{detector}_SUMMARY.csv")
    print(f"[{detector}/VUS] COMPLETE\n{summary.to_string(index=False)}", flush=True)


if __name__ == "__main__":
    main()
