"""Fast grouped implementation tests for redundant and irrelevant scores.

These synthetic tests validate evaluator semantics; they are not benchmark or
paper results.  Full controls still have to run on all 350 frozen series.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluate_cdu_protocol_v1 import (  # noqa: E402
    PROTOCOL_VERSION,
    SeriesRecord,
    aggregate_complete,
    average_rank01,
    evaluate_outer_source,
)


OUT = ROOT / "protocol_v1_results" / "sanity"
SOURCES = tuple(f"toy_source_{i}" for i in range(6))
SERIES_PER_SOURCE = 2
POINTS = 160


def make_records(control: str) -> list[SeriesRecord]:
    rng = np.random.default_rng(2024)
    records = []
    for source_index, source in enumerate(SOURCES):
        for series_index in range(SERIES_PER_SOURCE):
            n = POINTS + 7 * series_index
            raw_basis = rng.normal(size=(n, 31))
            basis = np.column_stack([average_rank01(raw_basis[:, j]) for j in range(31)])
            linear = (
                -2.0
                + 1.4 * (basis[:, 0] - 0.5)
                - 1.1 * (basis[:, 3] - 0.5)
                + 0.7 * (basis[:, 8] - 0.5)
                + 0.08 * (source_index - 2.5)
            )
            probability = 1.0 / (1.0 + np.exp(-linear))
            y = rng.binomial(1, probability).astype(np.int8)
            if control == "duplicate_basis":
                score = basis[:, 3].copy()
            elif control == "random_noise":
                score = average_rank01(rng.normal(size=n))
            else:
                raise ValueError(control)
            records.append(SeriesRecord(
                series_id=f"{source}_series_{series_index}",
                source_dataset=source,
                y=y,
                basis=basis,
                detector_score=score,
            ))
    return records


def run_control(control: str):
    records = make_records(control)
    pieces = []
    metadata = []
    for position, source in enumerate(SOURCES, 1):
        frame, meta = evaluate_outer_source(records, control, source)
        pieces.append(frame)
        metadata.append(meta)
        print(f"[{control}] outer source {position}/{len(SOURCES)} {source}: PASS", flush=True)
    result = pd.concat(pieces, ignore_index=True)
    summary, per_source = aggregate_complete(result)
    result.to_csv(OUT / f"{control}_per_series.csv", index=False)
    per_source.to_csv(OUT / f"{control}_per_source.csv", index=False)
    (OUT / f"{control}_hyperparameters.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    row = summary.iloc[0].to_dict()
    row["control"] = control
    row["unit_test_tolerance_bits"] = 0.01
    row["unit_test_status"] = "PASS" if abs(float(row["CDU"])) < 0.01 else "FAIL"
    return row


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [run_control("duplicate_basis"), run_control("random_noise")]
    frame = pd.DataFrame(rows)
    frame.to_csv(OUT / "SANITY_UNIT_TEST_SUMMARY.csv", index=False)
    lines = [
        "# Protocol v1 sanity unit tests",
        "",
        f"Protocol: `{PROTOCOL_VERSION}`",
        "",
        "These are deterministic synthetic grouped implementation tests, not TSB-AD-U paper results.",
        "The full 350-series duplicate/noise controls remain mandatory before detector interpretation.",
        "",
        frame[["control", "CDU", "CDU_CI_low", "CDU_CI_high", "positive_source_fraction", "unit_test_status"]].to_markdown(index=False),
        "",
        "A failure blocks the source-grouped detector run and requires an implementation/probe audit; results must not be tuned toward positivity.",
    ]
    (OUT / "SANITY_UNIT_TEST_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(frame[["control", "CDU", "CDU_CI_low", "CDU_CI_high", "unit_test_status"]].to_string(index=False))
    if (frame["unit_test_status"] != "PASS").any():
        raise SystemExit(2)


if __name__ == "__main__":
    main()
