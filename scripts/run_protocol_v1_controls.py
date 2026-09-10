"""Run formal 350-series protocol-v1 controls with shared frozen baselines."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Sequence

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluate_cdu_protocol_v1 import (  # noqa: E402
    C_GRID,
    EPS,
    PROTOCOL_VERSION,
    SEED,
    SeriesRecord,
    aggregate_complete,
    average_rank01,
    equal_source_series_weights,
    feature_matrix,
    grouped_inner_folds,
    log_loss_bits,
    make_probe,
    select_c,
    stack_training,
    weighted_training_prior,
)


OUT = ROOT / "protocol_v1_results" / "controls"
BASELINE = OUT / "shared_baseline"
DUPLICATE_COLUMN = "Var-96"
DUPLICATE_INDEX = 4
ALPHAS = (0.0, 0.25, 0.5, 1.0, 2.0)
NEGATIVE_CONTROLS = ("exact_duplicate_Var-96", "independent_noise")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_hash(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def run_signature_payload() -> dict:
    paths = (
        "protocol_v1.md",
        "source_groups.json",
        "protocol_v1_input_manifest.json",
        "protocol_v1_results/controls/SPLIT_MANIFEST.json",
        "scripts/evaluate_cdu_protocol_v1.py",
        "scripts/run_protocol_v1_controls.py",
    )
    hashes = {name: sha256_file(ROOT / name) for name in paths}
    config = {
        "protocol_version": PROTOCOL_VERSION,
        "seed": SEED,
        "C_grid": list(C_GRID),
        "duplicate_column": DUPLICATE_COLUMN,
        "duplicate_index": DUPLICATE_INDEX,
        "complementary_alphas": list(ALPHAS),
        "noise_seed_policy": "first 64 bits SHA256(protocol|series_id|control_name)",
        "class_weight": None,
        "aggregation": "timestamp mean -> series mean -> source mean",
    }
    return {"files": hashes, "config": config, "run_signature": canonical_hash({"files": hashes, "config": config})}


def enforce_signature() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "RUN_SIGNATURE.json"
    current = run_signature_payload()
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if old.get("run_signature") != current["run_signature"]:
            raise RuntimeError(
                "Formal-control checkpoint signature mismatch. Refusing to mix code/config/input versions."
            )
    else:
        path.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return current


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def atomic_json(value, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_basis_records() -> tuple[list[SeriesRecord], list[str]]:
    source_payload = json.loads((ROOT / "source_groups.json").read_text(encoding="utf-8"))
    input_manifest = json.loads((ROOT / "protocol_v1_input_manifest.json").read_text(encoding="utf-8"))
    expected_names = list(input_manifest["basis_names"])
    if expected_names[DUPLICATE_INDEX] != DUPLICATE_COLUMN:
        raise RuntimeError("Frozen duplicate basis index/name mismatch")
    records = []
    for position, series_id in enumerate(source_payload["series_order"], 1):
        path = ROOT / input_manifest["basis_files"][series_id]["relative_path"]
        with np.load(path, allow_pickle=False) as payload:
            basis = payload["basis"]
            y = payload["label"].astype(np.int8)
            names = list(map(str, payload["names"]))
        if names != expected_names:
            raise RuntimeError(f"Basis names drift at {series_id}")
        basis = basis.T if basis.shape[0] == 31 else basis
        if basis.shape != (len(y), 31) or not np.isfinite(basis).all():
            raise RuntimeError(f"Invalid basis cache at {series_id}")
        records.append(SeriesRecord(
            series_id=series_id,
            source_dataset=source_payload["series_to_source"][series_id],
            y=y,
            basis=np.asarray(basis, dtype=np.float32),
            # Baseline construction never consumes a detector score.  Keep an
            # empty placeholder to avoid allocating a full extra 350-series copy.
            detector_score=np.empty(0, dtype=float),
        ))
        if position % 25 == 0 or position == 350:
            print(f"[controls] basis inputs loaded {position}/350", flush=True)
    return records, expected_names


def deterministic_noise(series_id: str, name: str, n: int) -> np.ndarray:
    key = f"{PROTOCOL_VERSION}|{series_id}|{name}".encode("utf-8")
    seed = int.from_bytes(hashlib.sha256(key).digest()[:8], "little", signed=False)
    return np.random.default_rng(seed).standard_normal(n)


def control_records(base: Sequence[SeriesRecord], control: str, alpha: float | None = None) -> list[SeriesRecord]:
    records = []
    for record in base:
        if control == "exact_duplicate_Var-96":
            score = record.basis[:, DUPLICATE_INDEX].copy()
        elif control == "independent_noise":
            score = average_rank01(deterministic_noise(record.series_id, control, len(record.y))).astype(np.float32)
        elif control == "complementary":
            if alpha is None:
                raise ValueError("alpha is required")
            z = deterministic_noise(record.series_id, "complementary_base", len(record.y))
            score = average_rank01(z + float(alpha) * record.y).astype(np.float32)
        else:
            raise ValueError(control)
        records.append(SeriesRecord(
            series_id=record.series_id,
            source_dataset=record.source_dataset,
            y=record.y,
            basis=record.basis,
            detector_score=score,
        ))
    return records


def split_metadata(records: Sequence[SeriesRecord], held_source: str) -> dict:
    training_sources = sorted({r.source_dataset for r in records if r.source_dataset != held_source})
    return {
        "training_source_ids": training_sources,
        "inner_validation_source_ids": grouped_inner_folds(training_sources),
        "test_source_id": held_source,
        "random_seed": SEED,
    }


def compute_baseline_source(records: Sequence[SeriesRecord], held_source: str):
    train = [r for r in records if r.source_dataset != held_source]
    test = [r for r in records if r.source_dataset == held_source]
    c_basis, inner_losses, inner_details = select_c(
        train, "basis", return_details=True,
        progress_label=f"baseline/{held_source}/basis",
    )
    x, y, w = stack_training(train, "basis")
    model = make_probe(c_basis).fit(x, y, sample_weight=w)
    del x, y, w
    prior = float(np.clip(weighted_training_prior(train), EPS, 1.0 - EPS))
    rows = []
    for record in test:
        l0 = log_loss_bits(record.y, np.full(len(record.y), prior))
        lb = log_loss_bits(record.y, model.predict_proba(record.basis)[:, 1])
        rows.append({
            "series_id": record.series_id,
            "source_dataset": held_source,
            "outer_fold": held_source,
            "L_null": l0,
            "L_basis": lb,
            "basis_utility": l0 - lb,
            "C_basis": c_basis,
            "n_points": len(record.y),
            "n_anomalies": int(np.sum(record.y)),
            "protocol_version": PROTOCOL_VERSION,
        })
    metadata = split_metadata(records, held_source)
    metadata.update({
        "condition": "shared_baseline",
        "selected_hyperparameter": {"C_basis": c_basis},
        "inner_cv_loss": {"basis": inner_losses},
        "inner_cv_fold_details": {"basis": inner_details},
        "training_prior": prior,
    })
    return pd.DataFrame(rows), metadata


def ensure_baseline(records: Sequence[SeriesRecord], sources: Sequence[str]) -> None:
    signature = enforce_signature()["run_signature"]
    for position, source in enumerate(sources, 1):
        path = BASELINE / "by_source" / f"{source}.csv"
        meta_path = BASELINE / "by_source" / f"{source}.json"
        if path.exists() and meta_path.exists():
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            expected = sum(r.source_dataset == source for r in records)
            cached = pd.read_csv(path)
            if metadata.get("run_signature") == signature and len(cached) == expected and cached.series_id.nunique() == expected:
                print(f"[baseline] outer {position}/23 {source}: SKIP", flush=True)
                continue
            raise RuntimeError(f"Invalid baseline checkpoint for {source}")
        frame, metadata = compute_baseline_source(records, source)
        metadata["run_signature"] = signature
        atomic_csv(frame, path)
        atomic_json(metadata, meta_path)
        print(f"[baseline] outer {position}/23 {source}: PASS ({len(frame)} series)", flush=True)
    pieces = [pd.read_csv(BASELINE / "by_source" / f"{source}.csv") for source in sources]
    combined = pd.concat(pieces, ignore_index=True)
    if len(combined) != 350 or combined.series_id.nunique() != 350:
        raise RuntimeError("Shared baseline coverage failure")
    atomic_csv(combined, BASELINE / "BASELINE_PER_SERIES.csv")


def compute_control_source(
    records: Sequence[SeriesRecord], control_name: str, held_source: str,
    baseline: pd.DataFrame,
):
    train = [r for r in records if r.source_dataset != held_source]
    test = [r for r in records if r.source_dataset == held_source]
    selected = {}
    losses = {}
    models = {}
    for condition in ("detector", "basis_detector"):
        selected[condition], losses[condition], details = select_c(
            train, condition, return_details=True,
            progress_label=f"{control_name}/{held_source}/{condition}",
        )
        losses[f"{condition}_fold_details"] = details
        x, y, w = stack_training(train, condition)
        models[condition] = make_probe(selected[condition]).fit(x, y, sample_weight=w)
        del x, y, w
    base = baseline.set_index("series_id")
    rows = []
    for record in test:
        if record.series_id not in base.index:
            raise RuntimeError(f"Missing shared baseline for {record.series_id}")
        b = base.loc[record.series_id]
        ld = log_loss_bits(record.y, models["detector"].predict_proba(record.detector_score[:, None])[:, 1])
        lbd = log_loss_bits(
            record.y,
            models["basis_detector"].predict_proba(
                np.column_stack((record.basis, record.detector_score))
            )[:, 1],
        )
        rows.append({
            "series_id": record.series_id,
            "source_dataset": held_source,
            "detector": control_name,
            "outer_fold": held_source,
            "L_null": float(b.L_null),
            "L_basis": float(b.L_basis),
            "L_detector": ld,
            "L_basis_detector": lbd,
            "basis_utility": float(b.L_null - b.L_basis),
            "detector_utility": float(b.L_null - ld),
            "basis_detector_utility": float(b.L_null - lbd),
            "CDU": float(b.L_basis - lbd),
            "C_basis": float(b.C_basis),
            "C_detector": selected["detector"],
            "C_basis_detector": selected["basis_detector"],
            "n_points": len(record.y),
            "n_anomalies": int(np.sum(record.y)),
            "protocol_version": PROTOCOL_VERSION,
        })
    metadata = split_metadata(records, held_source)
    metadata.update({
        "condition": control_name,
        "selected_hyperparameter": {
            "C_basis": float(base.iloc[0].C_basis),
            "C_detector": selected["detector"],
            "C_basis_detector": selected["basis_detector"],
        },
        "inner_cv_loss": losses,
    })
    return pd.DataFrame(rows), metadata


def ensure_control(records: Sequence[SeriesRecord], control_name: str, sources: Sequence[str]) -> None:
    signature = enforce_signature()["run_signature"]
    baseline = pd.read_csv(BASELINE / "BASELINE_PER_SERIES.csv")
    directory = OUT / control_name
    for position, source in enumerate(sources, 1):
        path = directory / "by_source" / f"{source}.csv"
        meta_path = directory / "by_source" / f"{source}.json"
        if path.exists() and meta_path.exists():
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            expected = sum(r.source_dataset == source for r in records)
            cached = pd.read_csv(path)
            if metadata.get("run_signature") == signature and len(cached) == expected and cached.series_id.nunique() == expected:
                print(f"[{control_name}] outer {position}/23 {source}: SKIP", flush=True)
                continue
            raise RuntimeError(f"Invalid {control_name} checkpoint for {source}")
        frame, metadata = compute_control_source(records, control_name, source, baseline)
        metadata["run_signature"] = signature
        atomic_csv(frame, path)
        atomic_json(metadata, meta_path)
        print(f"[{control_name}] outer {position}/23 {source}: PASS ({len(frame)} series)", flush=True)
    pieces = [pd.read_csv(directory / "by_source" / f"{source}.csv") for source in sources]
    combined = pd.concat(pieces, ignore_index=True)
    if len(combined) != 350 or combined.series_id.nunique() != 350:
        raise RuntimeError(f"{control_name} coverage failure")
    if not np.isfinite(combined.select_dtypes(include=[np.number]).to_numpy()).all():
        raise RuntimeError(f"{control_name} contains non-finite values")
    atomic_csv(combined, directory / "PER_SERIES.csv")
    summary, per_source = aggregate_complete(combined)
    atomic_csv(summary, directory / "SUMMARY.csv")
    atomic_csv(per_source, directory / "PER_SOURCE.csv")


def all_control_names() -> list[str]:
    return list(NEGATIVE_CONTROLS) + [f"complementary_alpha_{str(a).replace('.', 'p')}" for a in ALPHAS]


def write_acceptance() -> bool:
    names = all_control_names()
    missing = [name for name in names if not (OUT / name / "PER_SERIES.csv").exists()]
    fold = pd.read_csv(OUT / "FOLD_AUDIT.csv")
    resume_path = OUT / "RESUME_CLEAN_REGRESSION_PASS.json"
    resume_pass = False
    if resume_path.exists() and (OUT / "RUN_SIGNATURE.json").exists():
        resume = json.loads(resume_path.read_text(encoding="utf-8"))
        signature = json.loads((OUT / "RUN_SIGNATURE.json").read_text(encoding="utf-8"))
        resume_pass = resume.get("status") == "PASS" and resume.get("run_signature") == signature.get("run_signature")
    checks = {
        "all_formal_controls_complete": not missing,
        "fold_audit_pass": bool((fold["split_status"] == "PASS").all()),
        "resume_clean_regression_pass": resume_pass,
    }
    summaries = []
    baseline_equal = True
    finite = True
    coverage = True
    reference = None
    if not missing:
        for name in names:
            frame = pd.read_csv(OUT / name / "PER_SERIES.csv").sort_values("series_id")
            summary = pd.read_csv(OUT / name / "SUMMARY.csv").iloc[0].to_dict()
            summary["control"] = name
            summaries.append(summary)
            current = frame[["series_id", "L_null", "L_basis"]].reset_index(drop=True)
            if reference is None:
                reference = current
            else:
                baseline_equal &= current.equals(reference)
            finite &= np.isfinite(frame.select_dtypes(include=[np.number]).to_numpy()).all()
            coverage &= len(frame) == 350 and frame.series_id.nunique() == 350
        summary_frame = pd.DataFrame(summaries)
        atomic_csv(summary_frame, OUT / "FORMAL_CONTROL_SUMMARY.csv")
        def row(name): return summary_frame[summary_frame.control == name].iloc[0]
        duplicate = row("exact_duplicate_Var-96")
        noise = row("independent_noise")
        comp = summary_frame[summary_frame.control.str.startswith("complementary_alpha_")].copy()
        comp["alpha"] = comp.control.str.removeprefix("complementary_alpha_").str.replace("p", ".", regex=False).astype(float)
        comp = comp.sort_values("alpha")
        trend = float(spearmanr(comp.alpha, comp.CDU).statistic)
        largest = comp.iloc[-1]
        checks.update({
            "duplicate_ci_covers_zero": float(duplicate.CDU_CI_low) <= 0 <= float(duplicate.CDU_CI_high),
            "noise_ci_covers_zero": float(noise.CDU_CI_low) <= 0 <= float(noise.CDU_CI_high),
            "negative_controls_not_significantly_positive": float(duplicate.CDU_CI_low) <= 0 and float(noise.CDU_CI_low) <= 0,
            "complementary_overall_increase": trend >= 0.8,
            "largest_complementary_ci_positive": float(largest.CDU_CI_low) > 0,
            "baseline_bitwise_equal_across_controls": baseline_equal,
            "all_losses_finite": bool(finite),
            "each_control_350_unique_series": bool(coverage),
        })
    else:
        checks.update({
            "duplicate_ci_covers_zero": False,
            "noise_ci_covers_zero": False,
            "negative_controls_not_significantly_positive": False,
            "complementary_overall_increase": False,
            "largest_complementary_ci_positive": False,
            "baseline_bitwise_equal_across_controls": False,
            "all_losses_finite": False,
            "each_control_350_unique_series": False,
        })
    go = all(checks.values())
    lines = [
        "# Formal control acceptance",
        "",
        f"Decision: **{'GO' if go else 'STOP / INCOMPLETE'}**",
        "",
        f"Missing controls: `{missing}`",
        "",
        "| Check | Status |",
        "|---|---|",
    ] + [f"| {name} | {'PASS' if status else 'FAIL/PENDING'} |" for name, status in checks.items()]
    (OUT / "CONTROL_ACCEPTANCE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return go


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("baseline", "negative", "complementary", "all", "audit"), default="all")
    args = parser.parse_args()
    signature = enforce_signature()
    print(f"formal-control run signature: {signature['run_signature']}", flush=True)
    if args.phase == "audit":
        write_acceptance()
        return
    base, names = load_basis_records()
    sources = sorted({r.source_dataset for r in base})
    ensure_baseline(base, sources)
    if args.phase in ("negative", "all"):
        for control in NEGATIVE_CONTROLS:
            records = control_records(base, control)
            ensure_control(records, control, sources)
            del records; gc.collect()
    if args.phase in ("complementary", "all"):
        for alpha in ALPHAS:
            name = f"complementary_alpha_{str(alpha).replace('.', 'p')}"
            records = control_records(base, "complementary", alpha)
            ensure_control(records, name, sources)
            del records; gc.collect()
    write_acceptance()


if __name__ == "__main__":
    main()
