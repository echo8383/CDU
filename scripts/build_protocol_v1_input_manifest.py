"""Hash frozen basis inputs and record audited detector-score hashes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
L2 = ROOT / "layer2_results"
OUTPUT = ROOT / "protocol_v1_input_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    source = json.loads((ROOT / "source_groups.json").read_text(encoding="utf-8"))
    files = source["series_order"]
    basis_entries = {}
    expected_names = None
    for position, series_id in enumerate(files, 1):
        path = L2 / "basis_scores" / f"{series_id}.npz"
        if not path.exists():
            raise FileNotFoundError(path)
        with np.load(path, allow_pickle=False) as payload:
            names = list(map(str, payload["names"]))
            basis_shape = list(payload["basis"].shape)
            label_shape = list(payload["label"].shape)
        if expected_names is None:
            expected_names = names
        elif names != expected_names:
            raise RuntimeError(f"Basis name/order drift at {series_id}")
        basis_entries[series_id] = {
            "relative_path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
            "basis_shape": basis_shape,
            "label_shape": label_shape,
        }
        if position % 25 == 0 or position == len(files):
            print(f"basis hashes {position}/{len(files)}", flush=True)

    audit_all = pd.read_csv(L2 / "STAGE2_SCORE_CACHE_AUDIT.csv")
    audit_all = audit_all[audit_all["series_id"].isin(files)].copy()
    audit = audit_all[(audit_all["status"] == "PASS") & (audit_all["cache_exists"] == True)].copy()  # noqa: E712
    if len(audit) != 9 * 350 or audit.duplicated(["detector", "series_id"]).any():
        raise RuntimeError("Unique PASS rows in the audited detector score manifest are incomplete")
    cache_dirs = {
        detector: (L2 / "poly_pinned_scores" if detector == "POLY" else L2 / "detector_scores" / detector)
        for detector in sorted(audit.detector.unique())
    }
    detector_entries = {}
    for detector, group in audit.groupby("detector"):
        entries = {}
        audit_hash = group.set_index("series_id")["score_hash"].astype(str).to_dict()
        for position, series_id in enumerate(files, 1):
            path = cache_dirs[str(detector)] / f"{series_id}.npy"
            score = np.load(path, allow_pickle=False).reshape(-1)
            content_hash = hashlib.sha256(np.ascontiguousarray(score, dtype=np.float64).tobytes()).hexdigest()
            if content_hash != audit_hash[series_id]:
                raise RuntimeError(f"Current score hash disagrees with PASS audit: {detector}/{series_id}")
            entries[series_id] = {
                "relative_path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "size_bytes": path.stat().st_size,
                "file_sha256": sha256(path),
                "float64_content_sha256": content_hash,
            }
        detector_entries[str(detector)] = entries
        print(f"detector hashes {detector}: {len(entries)}/350", flush=True)
    payload = {
        "protocol_version": "CDU-protocol-v1",
        "n_series": 350,
        "n_basis_features": 31,
        "basis_names": expected_names,
        "basis_files": basis_entries,
        "detector_score_hash_source": "Direct current-file SHA-256 cross-checked against unique cache_exists PASS rows in layer2_results/STAGE2_SCORE_CACHE_AUDIT.csv",
        "stage2_audit_duplicate_note": {
            "total_relevant_rows": int(len(audit_all)),
            "selected_unique_pass_rows": int(len(audit)),
            "ignored_stale_fail_rows": int(len(audit_all) - len(audit)),
            "reason": "The historical audit CSV contains a second stale missing-path row per detector-series; protocol v1 hashes current files directly and refuses hash disagreement.",
        },
        "detector_score_hashes": detector_entries,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}: basis=350, detectors={len(detector_entries)}")


if __name__ == "__main__":
    main()
