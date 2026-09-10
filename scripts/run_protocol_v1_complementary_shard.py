"""Run a disjoint subset of formal complementary controls on another host.

The authoritative runner/signature files are not modified. This helper calls
the same frozen evaluator and writes the same per-alpha output directories.
Each alpha must be owned by exactly one host while it is running.
"""
from __future__ import annotations

import argparse
import gc
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_protocol_v1_controls as controls  # noqa: E402


def alpha_name(alpha: float) -> str:
    return f"complementary_alpha_{str(alpha).replace('.', 'p')}"


def require_shared_baseline(sources: list[str]) -> None:
    root = controls.OUT / "shared_baseline"
    aggregate = root / "BASELINE_PER_SERIES.csv"
    if not aggregate.is_file() or len(pd.read_csv(aggregate)) != 350:
        raise RuntimeError("Shared baseline is missing/incomplete. Restore the collaborator asset bundle first.")
    missing = [source for source in sources if not (root / "by_source" / f"{source}.json").is_file()]
    if missing:
        raise RuntimeError(f"Shared baseline source checkpoints missing: {missing}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--alphas",
        nargs="+",
        type=float,
        required=True,
        help="Disjoint frozen alpha subset, e.g. --alphas 0 0.25 0.5 1 2",
    )
    args = parser.parse_args()
    allowed = set(float(value) for value in controls.ALPHAS)
    requested = list(dict.fromkeys(args.alphas))
    invalid = [value for value in requested if value not in allowed]
    if invalid:
        raise ValueError(f"Not in frozen alpha grid {sorted(allowed)}: {invalid}")

    signature = controls.enforce_signature()
    print(f"formal-control run signature: {signature['run_signature']}", flush=True)
    records, _ = controls.load_basis_records()
    sources = sorted({record.source_dataset for record in records})
    require_shared_baseline(sources)
    for alpha in requested:
        name = alpha_name(alpha)
        print(f"[collaborator] START {name}", flush=True)
        augmented = controls.control_records(records, "complementary", alpha)
        controls.ensure_control(augmented, name, sources)
        del augmented
        gc.collect()
        print(f"[collaborator] COMPLETE {name}", flush=True)
    print("COLLABORATOR COMPLEMENTARY SHARD COMPLETE", flush=True)


if __name__ == "__main__":
    main()
