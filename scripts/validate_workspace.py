"""Fail-fast validation for a fresh clone or a collaborator's mounted assets.

This does not run a detector and does not modify results. It reports which
task is possible with the files currently present.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def state(name: str, passed: bool, detail: str) -> bool:
    print(f"{'PASS' if passed else 'MISSING'} | {name}: {detail}")
    return passed


def main() -> int:
    required_ok = True
    index = ROOT / "uni_vuspr.csv"
    required_ok &= state("benchmark index", index.is_file(), str(index))
    series: list[str] = []
    if index.is_file():
        series = pd.read_csv(index)["file"].astype(str).tolist()
        required_ok &= state("benchmark cardinality", len(series) == 350, f"{len(series)} series")

    groups = ROOT / "source_groups.json"
    required_ok &= state("source map", groups.is_file(), str(groups))
    if groups.is_file():
        payload = json.loads(groups.read_text(encoding="utf-8"))
        mapping = payload.get("series_to_source", payload.get("mapping", {}))
        if mapping:
            required_ok &= state("source-map coverage", set(mapping) == set(series), f"{len(mapping)}/350")

    required_ok &= state("frozen protocol", (ROOT / "protocol_v1.md").is_file(), "protocol_v1.md")

    data_dir = ROOT / "Datasets" / "TSB-AD-U"
    data_present = sum((data_dir / series_id).is_file() for series_id in series)
    state("raw TSB-AD-U benchmark files", data_present == 350, f"{data_present}/350 indexed files at {data_dir}")

    basis_dir = ROOT / "layer2_results" / "basis_scores"
    n_basis = len(list(basis_dir.glob("*.npz"))) if basis_dir.is_dir() else 0
    state("basis cache", n_basis == 350, f"{n_basis}/350 at {basis_dir}")

    detectors = ["SubPCA", "POLY", "MOMENT_FT", "MOMENT_ZS", "M2N2", "TranAD", "TimesNet", "FITS", "AnomalyTransformer"]
    for detector in detectors:
        score_dir = ROOT / ("layer2_results/poly_pinned_scores" if detector == "POLY" else f"layer2_results/detector_scores/{detector}")
        count = len(list(score_dir.glob("*.npy"))) if score_dir.is_dir() else 0
        state(f"{detector} score cache", count == 350, f"{count}/350 at {score_dir}")

    tsb = os.environ.get("TSB_AD_ROOT")
    valid_tsb = bool(tsb and (Path(tsb).expanduser() / "TSB_AD").is_dir())
    state("TSB_AD_ROOT", valid_tsb, tsb or "not set (needed only for detector sweeps)")

    print("\nProtocol-v1 controls/main evaluation need index + source map + basis cache + relevant score cache.")
    print("Detector sweeps additionally need raw data + TSB_AD_ROOT + the pinned TSB-AD environment.")
    return 0 if required_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
