"""Generate and validate the frozen source-grouped outer/inner folds."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluate_cdu_protocol_v1 import grouped_inner_folds  # noqa: E402


OUT = ROOT / "protocol_v1_results" / "controls"


def canonical_hash(value) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    payload = json.loads((ROOT / "source_groups.json").read_text(encoding="utf-8"))
    all_sources = sorted(payload["groups"])
    series_to_source = payload["series_to_source"]
    rows = []
    manifest = {"protocol_version": "CDU-protocol-v1", "seed": 2024, "outer_folds": []}
    held_series = []
    for outer_index, test_source in enumerate(all_sources):
        train_sources = [source for source in all_sources if source != test_source]
        inner = grouped_inner_folds(train_sources)
        outer_item = {
            "outer_fold_index": outer_index,
            "test_source": test_source,
            "training_sources": train_sources,
            "inner_validation_sources": inner,
        }
        manifest["outer_folds"].append(outer_item)
        held_series.extend(payload["groups"][test_source])
        for inner_index, validation_sources in enumerate(inner):
            validation = set(validation_sources)
            inner_train = [source for source in train_sources if source not in validation]
            test = {test_source}
            pass_outer_train = not (test & set(train_sources))
            pass_outer_validation = not (test & validation)
            pass_inner = not (set(inner_train) & validation)
            union_pass = set(inner_train) | validation == set(train_sources)
            rows.append({
                "outer_fold_index": outer_index,
                "outer_test_source": test_source,
                "inner_fold_index": inner_index,
                "outer_training_sources": json.dumps(train_sources),
                "inner_training_sources": json.dumps(inner_train),
                "inner_validation_sources": json.dumps(validation_sources),
                "n_outer_test_series": len(payload["groups"][test_source]),
                "n_outer_training_sources": len(train_sources),
                "n_inner_training_sources": len(inner_train),
                "n_inner_validation_sources": len(validation_sources),
                "outer_test_in_outer_train": len(test & set(train_sources)),
                "outer_test_in_inner_validation": len(test & validation),
                "inner_train_validation_overlap": len(set(inner_train) & validation),
                "inner_partition_covers_outer_train": union_pass,
                "split_status": "PASS" if all((pass_outer_train, pass_outer_validation, pass_inner, union_pass)) else "FAIL",
            })
    unique_held = set(held_series)
    population = set(series_to_source)
    manifest["n_sources"] = len(all_sources)
    manifest["n_series"] = len(population)
    manifest["series_held_out_exactly_once"] = len(held_series) == len(unique_held) == len(population) == 350
    manifest["split_sha256"] = canonical_hash(manifest["outer_folds"])
    frame = pd.DataFrame(rows)
    if (frame["split_status"] != "PASS").any() or not manifest["series_held_out_exactly_once"]:
        raise RuntimeError("Source-grouped fold audit failed")
    OUT.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUT / "FOLD_AUDIT.csv", index=False)
    (OUT / "SPLIT_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"FOLD AUDIT PASS: outer={len(all_sources)}, inner rows={len(frame)}, "
        f"series exactly once={manifest['series_held_out_exactly_once']}, "
        f"split_sha256={manifest['split_sha256']}"
    )


if __name__ == "__main__":
    main()
