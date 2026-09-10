"""Write a SHA-256/environment manifest for the protocol-v1 contract."""
from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import numpy
import pandas
import scipy
import sklearn


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "protocol_v1_manifest.json"
FILES = (
    "protocol_v1.md",
    "source_groups.json",
    "uni_vuspr.csv",
    "layer2_results/STAGE2_DETECTOR_PROVENANCE.csv",
    "layer2_results/STAGE2_SCORE_CACHE_AUDIT.csv",
    "layer2_results/STAGE2_AUDITED_LEADERBOARD.csv",
    "scripts/build_source_groups.py",
    "scripts/evaluate_cdu_protocol_v1.py",
    "scripts/test_protocol_v1_sanity.py",
    "scripts/audit_protocol_v1_folds.py",
    "scripts/build_protocol_v1_input_manifest.py",
    "scripts/run_protocol_v1_controls.py",
    "scripts/verify_protocol_v1_resume_clean.py",
    "protocol_v1_input_manifest.json",
    "protocol_v1_results/controls/FOLD_AUDIT.csv",
    "protocol_v1_results/controls/SPLIT_MANIFEST.json",
    "STAGE2_SCORE_CACHE_AUDIT_DUPLICATE_NOTE.md",
    "paper/icassp2027/main.tex",
    "paper/icassp2027/references.bib",
    "protocol_v1_results/sanity/SANITY_UNIT_TEST_SUMMARY.csv",
    "protocol_v1_results/sanity/SANITY_UNIT_TEST_REPORT.md",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    missing = [name for name in FILES if not (ROOT / name).exists()]
    if missing:
        raise FileNotFoundError(f"Cannot freeze protocol; missing: {missing}")
    source = json.loads((ROOT / "source_groups.json").read_text(encoding="utf-8"))
    payload = {
        "protocol_version": "CDU-protocol-v1",
        "frozen_date": "2026-08-30",
        "project_git_commit": None,
        "project_git_note": "The CDU kit directory is not a Git worktree; core artifacts are frozen by SHA-256.",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": {
            "numpy": numpy.__version__,
            "pandas": pandas.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "population": {
            "n_series": source["n_series"],
            "n_sources": source["n_sources"],
            "source_counts": source["source_counts"],
        },
        "files": {name: sha256(ROOT / name) for name in FILES},
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT} with {len(FILES)} hashed artifacts")


if __name__ == "__main__":
    main()
