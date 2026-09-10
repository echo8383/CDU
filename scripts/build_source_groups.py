"""Build the frozen TSB-AD-U source grouping used by CDU protocol v1."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "uni_vuspr.csv"
OUTPUT = ROOT / "source_groups.json"
SOURCE_PATTERN = re.compile(r"^\d+_([^_]+)_")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_from_series_id(series_id: str) -> str:
    match = SOURCE_PATTERN.match(series_id)
    if match is None:
        raise ValueError(f"Cannot parse source dataset from {series_id!r}")
    return match.group(1)


def main() -> None:
    frame = pd.read_csv(INDEX)
    series = frame["file"].astype(str).tolist()
    if len(series) != 350 or len(set(series)) != 350:
        raise RuntimeError(f"Expected 350 unique series, found {len(series)}/{len(set(series))}")

    series_to_source = {item: source_from_series_id(item) for item in series}
    groups: dict[str, list[str]] = {}
    for item in series:
        groups.setdefault(series_to_source[item], []).append(item)
    groups = dict(sorted(groups.items()))

    payload = {
        "protocol_version": "CDU-protocol-v1",
        "frozen_date": "2026-08-30",
        "benchmark": "TSB-AD-U frozen 350-series population",
        "benchmark_index": "uni_vuspr.csv",
        "benchmark_index_sha256": sha256(INDEX),
        "grouping_unit": "source_dataset",
        "grouping_rule": "Exact source token captured by ^\\d+_([^_]+)_ in the frozen series_id.",
        "grouping_notes": [
            "This is not the semantic dataset_family used by the trivial-hard analysis.",
            "No label, detector score, VUS, or CDU value is used to construct a group.",
            "MSL and SMAP remain distinct benchmark source datasets under this mechanical rule.",
            "All UCR series are conservatively grouped under the UCR source archive.",
        ],
        "n_series": len(series),
        "n_sources": len(groups),
        "source_counts": {source: len(items) for source, items in groups.items()},
        "series_order": series,
        "series_to_source": series_to_source,
        "groups": groups,
        "unresolved_series": [],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}: {len(series)} series, {len(groups)} source datasets")
    for source, items in groups.items():
        print(f"{source:12s} {len(items):3d}")


if __name__ == "__main__":
    main()
