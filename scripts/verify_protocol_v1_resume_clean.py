"""Recompute one formal source cleanly and compare with resumed checkpoints."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_protocol_v1_controls import (  # noqa: E402
    BASELINE,
    NEGATIVE_CONTROLS,
    OUT,
    compute_baseline_source,
    compute_control_source,
    control_records,
    load_basis_records,
)


VERIFY_SOURCE = "UCR"


def canonical_frame_hash(frame: pd.DataFrame) -> str:
    frame = frame.sort_values("series_id").reset_index(drop=True)
    text = frame.to_csv(index=False, lineterminator="\n", float_format="%.17g")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def exact_numeric_equal(left: pd.DataFrame, right: pd.DataFrame) -> bool:
    left = left.sort_values("series_id").reset_index(drop=True)
    right = right.sort_values("series_id").reset_index(drop=True)
    if list(left.columns) != list(right.columns) or len(left) != len(right):
        return False
    for column in left.columns:
        if pd.api.types.is_numeric_dtype(left[column]):
            if not np.array_equal(left[column].to_numpy(), right[column].to_numpy()):
                return False
        elif not left[column].equals(right[column]):
            return False
    return True


def main() -> None:
    signature_path = OUT / "RUN_SIGNATURE.json"
    if not signature_path.exists():
        raise RuntimeError("No formal-control run signature")
    signature = json.loads(signature_path.read_text(encoding="utf-8"))["run_signature"]
    base, _ = load_basis_records()
    cached_baseline = pd.read_csv(BASELINE / "by_source" / f"{VERIFY_SOURCE}.csv")
    clean_baseline, _ = compute_baseline_source(base, VERIFY_SOURCE)
    checks = {
        "baseline_exact": exact_numeric_equal(cached_baseline, clean_baseline),
        "baseline_cached_hash": canonical_frame_hash(cached_baseline),
        "baseline_clean_hash": canonical_frame_hash(clean_baseline),
    }
    for control in NEGATIVE_CONTROLS:
        records = control_records(base, control)
        cached = pd.read_csv(OUT / control / "by_source" / f"{VERIFY_SOURCE}.csv")
        clean, _ = compute_control_source(records, control, VERIFY_SOURCE, clean_baseline)
        checks[f"{control}_exact"] = exact_numeric_equal(cached, clean)
        checks[f"{control}_cached_hash"] = canonical_frame_hash(cached)
        checks[f"{control}_clean_hash"] = canonical_frame_hash(clean)
    exact_keys = [key for key in checks if key.endswith("_exact")]
    status = "PASS" if all(checks[key] for key in exact_keys) else "FAIL"
    payload = {
        "protocol_version": "CDU-protocol-v1",
        "run_signature": signature,
        "verification_source": VERIFY_SOURCE,
        "scope": "shared baseline plus both formal negative controls",
        "status": status,
        "checks": checks,
    }
    path = OUT / "RESUME_CLEAN_REGRESSION_PASS.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if status != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
