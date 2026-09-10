"""Source-grouped four-loss evaluator for frozen CDU protocol v1.

This script never executes a detector.  It consumes only the audited point-wise
score caches and the frozen 31-dimensional basis cache.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.linear_model import LogisticRegression


ROOT = Path(__file__).resolve().parents[1]
LAYER2 = ROOT / "layer2_results"
RESULTS = ROOT / "protocol_v1_results"
PROTOCOL_VERSION = "CDU-protocol-v1"
SEED = 2024
C_GRID = (0.01, 0.1, 1.0, 10.0)
EPS = 1e-7
DETECTORS = (
    "SubPCA", "POLY", "MOMENT_FT", "MOMENT_ZS", "M2N2", "TranAD",
    "TimesNet", "FITS", "AnomalyTransformer",
)
CACHE_DIRS = {
    detector: (LAYER2 / "poly_pinned_scores" if detector == "POLY"
               else LAYER2 / "detector_scores" / detector)
    for detector in DETECTORS
}


@dataclass
class SeriesRecord:
    series_id: str
    source_dataset: str
    y: np.ndarray
    basis: np.ndarray
    detector_score: np.ndarray


def average_rank01(values: np.ndarray) -> np.ndarray:
    """Label-free average-rank normalization; constants map to 0.5."""
    values = np.asarray(values, dtype=float).reshape(-1)
    if not np.isfinite(values).all():
        raise ValueError("Non-finite score passed to rank normalization")
    if len(values) == 0:
        raise ValueError("Empty score")
    if np.ptp(values) == 0:
        return np.full(len(values), 0.5, dtype=float)
    return (rankdata(values, method="average") - 0.5) / len(values)


def load_source_map() -> dict[str, str]:
    payload = json.loads((ROOT / "source_groups.json").read_text(encoding="utf-8"))
    if payload["protocol_version"] != PROTOCOL_VERSION:
        raise RuntimeError("source_groups.json protocol version mismatch")
    if payload["n_series"] != 350 or payload["unresolved_series"]:
        raise RuntimeError("source grouping is incomplete")
    return {str(k): str(v) for k, v in payload["series_to_source"].items()}


def load_detector_records(detector: str) -> list[SeriesRecord]:
    if detector not in DETECTORS:
        raise ValueError(f"Unsupported detector {detector}")
    source_map = load_source_map()
    files = pd.read_csv(ROOT / "uni_vuspr.csv")["file"].astype(str).tolist()
    cache_dir = CACHE_DIRS[detector]
    records: list[SeriesRecord] = []
    expected_names: tuple[str, ...] | None = None
    for position, series_id in enumerate(files, 1):
        basis_path = LAYER2 / "basis_scores" / f"{series_id}.npz"
        score_path = cache_dir / f"{series_id}.npy"
        with np.load(basis_path, allow_pickle=False) as payload:
            basis = payload["basis"]
            y = payload["label"].astype(np.int8)
            names = tuple(map(str, payload["names"]))
        if basis.ndim != 2:
            raise RuntimeError(f"Invalid basis shape for {series_id}: {basis.shape}")
        if basis.shape[0] == 31:
            basis = basis.T
        if basis.shape != (len(y), 31):
            raise RuntimeError(f"Basis/label mismatch for {series_id}: {basis.shape}/{len(y)}")
        if expected_names is None:
            expected_names = names
        elif names != expected_names:
            raise RuntimeError(f"Basis name/order drift for {series_id}")
        if not np.isfinite(basis).all() or np.min(basis) < 0 or np.max(basis) > 1:
            raise RuntimeError(f"Invalid frozen basis values for {series_id}")
        detector_score = np.load(score_path, allow_pickle=False).reshape(-1)
        if len(detector_score) != len(y):
            raise RuntimeError(f"Detector/label mismatch for {series_id}")
        detector_score = average_rank01(detector_score)
        records.append(SeriesRecord(
            series_id=series_id,
            source_dataset=source_map[series_id],
            y=y,
            basis=np.asarray(basis, dtype=np.float32),
            detector_score=np.asarray(detector_score, dtype=np.float32),
        ))
        if position % 25 == 0 or position == len(files):
            print(f"[{detector}] loaded {position}/{len(files)}", flush=True)
    return records


def feature_matrix(record: SeriesRecord, condition: str) -> np.ndarray:
    if condition == "basis":
        return record.basis
    if condition == "detector":
        return record.detector_score[:, None]
    if condition == "basis_detector":
        return np.column_stack((record.basis, record.detector_score))
    raise ValueError(condition)


def grouped_inner_folds(training_sources: Sequence[str], seed: int = SEED) -> list[list[str]]:
    sources = np.asarray(sorted(set(training_sources)), dtype=object)
    if len(sources) < 5:
        raise ValueError("At least five training sources are required")
    shuffled = np.random.default_rng(seed).permutation(sources)
    return [list(map(str, block)) for block in np.array_split(shuffled, 5)]


def equal_source_series_weights(records: Sequence[SeriesRecord]) -> list[np.ndarray]:
    source_counts: dict[str, int] = {}
    for record in records:
        source_counts[record.source_dataset] = source_counts.get(record.source_dataset, 0) + 1
    n_sources = len(source_counts)
    total_points = sum(len(record.y) for record in records)
    weights = []
    for record in records:
        raw = 1.0 / (n_sources * source_counts[record.source_dataset] * len(record.y))
        weights.append(np.full(len(record.y), raw * total_points, dtype=float))
    return weights


def stack_training(records: Sequence[SeriesRecord], condition: str):
    x = np.vstack([feature_matrix(record, condition) for record in records])
    y = np.concatenate([record.y for record in records])
    w = np.concatenate(equal_source_series_weights(records))
    return x, y, w


def make_probe(c_value: float) -> LogisticRegression:
    return LogisticRegression(
        C=float(c_value), penalty="l2", solver="liblinear", class_weight=None,
        max_iter=300, random_state=SEED,
    )


def log_loss_bits(y: np.ndarray, probability: np.ndarray) -> float:
    p = np.clip(np.asarray(probability, dtype=float), EPS, 1.0 - EPS)
    y = np.asarray(y, dtype=float)
    return float(np.mean(-(y * np.log2(p) + (1.0 - y) * np.log2(1.0 - p))))


def source_macro_loss(model, records: Sequence[SeriesRecord], condition: str) -> float:
    per_source: dict[str, list[float]] = {}
    for record in records:
        probability = model.predict_proba(feature_matrix(record, condition))[:, 1]
        per_source.setdefault(record.source_dataset, []).append(log_loss_bits(record.y, probability))
    return float(np.mean([np.mean(values) for values in per_source.values()]))


def select_c(
    records: Sequence[SeriesRecord], condition: str,
    c_grid: Sequence[float] = C_GRID, return_details: bool = False,
    progress_label: str | None = None,
):
    sources = [record.source_dataset for record in records]
    folds = grouped_inner_folds(sources)
    losses = {float(c): [] for c in c_grid}
    fold_details = []
    for fold_index, held_sources in enumerate(folds):
        held = set(held_sources)
        inner_train = [record for record in records if record.source_dataset not in held]
        inner_test = [record for record in records if record.source_dataset in held]
        x, y, w = stack_training(inner_train, condition)
        fold_loss = {}
        for c_index, c_value in enumerate(c_grid, 1):
            model = make_probe(c_value).fit(x, y, sample_weight=w)
            value = source_macro_loss(model, inner_test, condition)
            losses[float(c_value)].append(value)
            fold_loss[str(float(c_value))] = value
            if progress_label:
                print(
                    f"[{progress_label}] inner {fold_index + 1}/5 "
                    f"C {c_index}/{len(c_grid)}={float(c_value):g} "
                    f"source_macro_loss={value:.12g}",
                    flush=True,
                )
        fold_details.append({
            "inner_fold_index": fold_index,
            "training_source_ids": sorted({r.source_dataset for r in inner_train}),
            "validation_source_ids": sorted(held),
            "source_macro_loss_by_C": fold_loss,
        })
        del x, y, w
    means = {c: float(np.mean(values)) for c, values in losses.items()}
    selected = min(means, key=lambda c: (means[c], c))
    if return_details:
        return float(selected), means, fold_details
    return float(selected), means


def weighted_training_prior(records: Sequence[SeriesRecord]) -> float:
    y = np.concatenate([record.y for record in records])
    w = np.concatenate(equal_source_series_weights(records))
    return float(np.average(y, weights=w))


def evaluate_outer_source(
    records: Sequence[SeriesRecord], detector: str, held_source: str,
    c_grid: Sequence[float] = C_GRID,
) -> tuple[pd.DataFrame, dict]:
    train = [record for record in records if record.source_dataset != held_source]
    test = [record for record in records if record.source_dataset == held_source]
    if not test:
        raise ValueError(f"No test series for source {held_source}")
    selected: dict[str, float] = {}
    cv_losses: dict[str, dict] = {}
    models = {}
    for condition in ("basis", "detector", "basis_detector"):
        selected[condition], cv_losses[condition] = select_c(train, condition, c_grid)
        x, y, w = stack_training(train, condition)
        models[condition] = make_probe(selected[condition]).fit(x, y, sample_weight=w)
        del x, y, w
    prior = float(np.clip(weighted_training_prior(train), EPS, 1.0 - EPS))
    rows = []
    for record in test:
        l0 = log_loss_bits(record.y, np.full(len(record.y), prior))
        lb = log_loss_bits(record.y, models["basis"].predict_proba(record.basis)[:, 1])
        ld = log_loss_bits(record.y, models["detector"].predict_proba(record.detector_score[:, None])[:, 1])
        lbd = log_loss_bits(
            record.y,
            models["basis_detector"].predict_proba(
                np.column_stack((record.basis, record.detector_score))
            )[:, 1],
        )
        rows.append({
            "series_id": record.series_id,
            "source_dataset": record.source_dataset,
            "detector": detector,
            "outer_fold": held_source,
            "L_null": l0,
            "L_basis": lb,
            "L_detector": ld,
            "L_basis_detector": lbd,
            "basis_utility": l0 - lb,
            "detector_utility": l0 - ld,
            "CDU": lb - lbd,
            "C_basis": selected["basis"],
            "C_detector": selected["detector"],
            "C_basis_detector": selected["basis_detector"],
            "n_points": len(record.y),
            "protocol_version": PROTOCOL_VERSION,
        })
    metadata = {
        "outer_source": held_source,
        "n_train_sources": len(set(record.source_dataset for record in train)),
        "n_train_series": len(train),
        "n_test_series": len(test),
        "training_prior": prior,
        "selected_C": selected,
        "inner_cv_source_macro_losses": cv_losses,
    }
    return pd.DataFrame(rows), metadata


def cluster_bootstrap(values: pd.Series, n_boot: int = 10_000, seed: int = SEED):
    array = values.to_numpy(float)
    rng = np.random.default_rng(seed)
    draws = np.mean(array[rng.integers(0, len(array), size=(n_boot, len(array)))], axis=1)
    return float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5)), float(np.mean(draws > 0))


def aggregate_complete(frame: pd.DataFrame) -> pd.DataFrame:
    source = frame.groupby(["detector", "source_dataset"], as_index=False).agg(
        L_null=("L_null", "mean"),
        L_basis=("L_basis", "mean"),
        L_detector=("L_detector", "mean"),
        L_basis_detector=("L_basis_detector", "mean"),
        basis_utility=("basis_utility", "mean"),
        detector_utility=("detector_utility", "mean"),
        CDU=("CDU", "mean"),
        n_series=("series_id", "count"),
    )
    summaries = []
    for detector, group in source.groupby("detector"):
        low, high, probability = cluster_bootstrap(group["CDU"])
        summaries.append({
            "detector": detector,
            "L_null": group["L_null"].mean(),
            "L_basis": group["L_basis"].mean(),
            "L_detector": group["L_detector"].mean(),
            "L_basis_detector": group["L_basis_detector"].mean(),
            "basis_utility": group["basis_utility"].mean(),
            "detector_utility": group["detector_utility"].mean(),
            "CDU": group["CDU"].mean(),
            "CDU_CI_low": low,
            "CDU_CI_high": high,
            "positive_source_fraction": float(np.mean(group["CDU"] > 0)),
            "bootstrap_prob_source_macro_positive": probability,
            "n_sources": len(group),
            "n_series": int(group["n_series"].sum()),
            "protocol_version": PROTOCOL_VERSION,
        })
    return pd.DataFrame(summaries), source


def run_detector(detector: str, resume: bool) -> None:
    RESULTS.mkdir(exist_ok=True)
    per_series_path = RESULTS / f"{detector}_four_losses_per_series.csv"
    hyper_path = RESULTS / f"{detector}_selected_hyperparameters.jsonl"
    records = load_detector_records(detector)
    sources = sorted(set(record.source_dataset for record in records))
    completed: set[str] = set()
    if resume and per_series_path.exists():
        old = pd.read_csv(per_series_path)
        expected = {source: sum(r.source_dataset == source for r in records) for source in sources}
        actual = old.groupby("source_dataset")["series_id"].nunique().to_dict()
        completed = {source for source in sources if actual.get(source, 0) == expected[source]}
        print(f"[{detector}] resume: {len(completed)}/{len(sources)} sources complete", flush=True)
    for position, source in enumerate(sources, 1):
        if source in completed:
            print(f"[{detector}] outer {position}/{len(sources)} {source}: SKIP", flush=True)
            continue
        result, metadata = evaluate_outer_source(records, detector, source)
        result.to_csv(per_series_path, mode="a", header=not per_series_path.exists(), index=False)
        with hyper_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(metadata, sort_keys=True) + "\n")
        print(f"[{detector}] outer {position}/{len(sources)} {source}: PASS ({len(result)} series)", flush=True)
    final = pd.read_csv(per_series_path)
    if final["series_id"].nunique() != 350 or len(final) != 350:
        raise RuntimeError("Incomplete or duplicate per-series output; aggregation refused")
    summary, source = aggregate_complete(final)
    summary.to_csv(RESULTS / f"{detector}_source_macro_summary.csv", index=False)
    source.to_csv(RESULTS / f"{detector}_per_source.csv", index=False)
    print(summary.to_string(index=False), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--detector", choices=DETECTORS)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.all == bool(args.detector):
        parser.error("choose exactly one of --detector or --all")
    selected: Iterable[str] = DETECTORS if args.all else (args.detector,)
    source_map = load_source_map()
    print(f"Protocol {PROTOCOL_VERSION}: {len(source_map)} series, {len(set(source_map.values()))} sources")
    if args.dry_run:
        for detector in selected:
            missing = [series for series in source_map if not (CACHE_DIRS[detector] / f"{series}.npy").exists()]
            print(f"{detector}: {'PASS' if not missing else 'FAIL'} missing={len(missing)}")
        return
    for detector in selected:
        run_detector(detector, resume=args.resume)


if __name__ == "__main__":
    main()
