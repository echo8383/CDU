"""POLY-only Layer-2 CDU engineering pilot (R0-passing sequences only).

This script deliberately does not run any detector.  It consumes the already
screened, official-compatible POLY score cache and existing basis caches for
three sequences, writes auditable point-wise files, runs controls, and only
then writes the POLY pilot CDU result.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

import layer2_pilot as lp

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Datasets" / "TSB-AD-U"
L2 = ROOT / "layer2_results"
SCORE_DIR = L2 / "r0_runner_scores" / "POLY"
BASIS_DIR = L2 / "basis_scores"

FILES = [
    "010_NAB_id_10_WebService_tr_500_1st_271.csv",
    "039_WSD_id_11_WebService_tr_1746_1st_1846.csv",
    "331_UCR_id_29_Facility_tr_50000_1st_837400.csv",
]
WINDOWS = {FILES[0]: 142, FILES[1]: 125, FILES[2]: 125}
COMMIT = "8b363e350ae047a8115a594d1e9da64aae09b852"
SEED = 2024


def sha256_array(x: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()


def load_aligned(file: str):
    d = pd.read_csv(DATA / file).dropna()
    y = d["Label"].to_numpy(np.int8)
    score = np.load(SCORE_DIR / (file + ".npy"), allow_pickle=False).astype(float)
    z = np.load(BASIS_DIR / (file + ".npz"), allow_pickle=False)
    B = np.asarray(z["basis"], dtype=float)
    names = [str(x) for x in z["names"].tolist()]
    # Existing cache was written as (31,T); normalize orientation explicitly.
    if B.shape == (len(y), 31):
        pass
    elif B.shape == (31, len(y)):
        B = B.T
    else:
        raise ValueError(f"basis shape {B.shape} incompatible with {file}, T={len(y)}")
    if len(score) != len(y):
        raise ValueError(f"score/label mismatch for {file}: {len(score)} vs {len(y)}")
    if not np.isfinite(score).all() or not np.isfinite(B).all():
        raise ValueError(f"non-finite score/basis in {file}")
    return y, score, B, names


def write_pointwise():
    provenance = []
    curves = {}
    parity = pd.read_csv(L2 / "r0_official_compat_parity.csv")
    score_path = L2 / "poly_scores.csv"
    basis_path = L2 / "poly_basis_scores.csv"
    reuse = score_path.exists() and basis_path.exists()
    if reuse:
        return {f: np.load(SCORE_DIR / (f + ".npy"), allow_pickle=False).astype(float) for f in FILES}, [
            {"series_id": f, "length": len(load_aligned(f)[0]), "finite_ratio": 1.0,
             "window": WINDOWS[f], "score_sha256": sha256_array(load_aligned(f)[1]),
             "label_sha256": sha256_array(load_aligned(f)[0]),
            "official_vus": float(pd.read_csv(ROOT / "uni_vuspr.csv").set_index("file").loc[f, "POLY"]),
            "reproduced_vus": float(parity.query("detector == 'POLY' and series_id == @f").compat_vus.iloc[0]),
            "vus_abs_diff": float(parity.query("detector == 'POLY' and series_id == @f").abs_diff.iloc[0]),
             "score_min": float(load_aligned(f)[1].min()), "score_max": float(load_aligned(f)[1].max())} for f in FILES]
    for path in (score_path, basis_path):
        if path.exists(): path.unlink()
    score_header = True; basis_header = True
    for file in FILES:
        y, score, Braw, names = load_aligned(file)
        # Basis cache contains raw curves; CDU protocol uses per-series ranks.
        B = np.column_stack([lp.rank01(Braw[:, j]) for j in range(Braw.shape[1])])
        srank = lp.rank01(score)
        curves[file] = score
        sid = file
        score_df = pd.DataFrame({"series_id": sid, "timestamp": np.arange(len(y), dtype=np.int64),
                                 "score": score, "score_rank": srank, "label": y})
        score_df.to_csv(score_path, mode="a", header=score_header, index=False)
        score_header = False
        basis_df = pd.DataFrame(B, columns=names)
        basis_df.insert(0, "label", y)
        basis_df.insert(0, "timestamp", np.arange(len(y), dtype=np.int64))
        basis_df.insert(0, "series_id", sid)
        basis_df.to_csv(basis_path, mode="a", header=basis_header, index=False)
        basis_header = False
        official = float(pd.read_csv(ROOT / "uni_vuspr.csv").set_index("file").loc[file, "POLY"])
        pr = parity[(parity.detector == "POLY") & (parity.series_id == file)].iloc[0]
        provenance.append({
            "series_id": file, "length": len(y), "finite_ratio": float(np.isfinite(score).mean()),
            "window": WINDOWS[file], "score_sha256": sha256_array(score),
            "label_sha256": sha256_array(y), "official_vus": official,
            "reproduced_vus": float(pr.compat_vus), "vus_abs_diff": float(pr.abs_diff),
            "score_min": float(score.min()), "score_max": float(score.max()),
        })
    return curves, provenance


def run_controls_and_cdu(curves):
    # 3-fold is the maximum non-empty whole-series OOF split for this pilot.
    files = FILES
    ctrl = []
    var = {}
    labels = {}
    data = {}
    for f in files:
        B, y, names = lp.cache_basis(f)
        B = np.asarray(B, dtype=float)
        B = np.column_stack([lp.rank01(B[:, j]) for j in range(B.shape[1])])
        # cache_basis returns (T,31), and its values are rank-normalized only
        # when generated by the current code; enforce rank normalization.
        j = names.index("Var-96")
        var[f] = B[:, j]
        labels[f] = np.asarray(y, dtype=np.int8)
        data[f] = (B, labels[f])

    m0_cache = None
    def fast_oof(det_curves):
        nonlocal m0_cache
        blocks = np.array_split(np.arange(len(files)), 3)
        rows = []
        for k, test_ids in enumerate(blocks):
            if len(test_ids) == 0:
                continue
            train_ids = np.concatenate([b for j, b in enumerate(blocks) if j != k])
            X0 = np.vstack([data[files[i]][0] for i in train_ids])
            X1 = np.vstack([np.column_stack([data[files[i]][0], lp.rank01(det_curves[files[i]])]) for i in train_ids])
            Y = np.concatenate([data[files[i]][1] for i in train_ids])
            m0 = LogisticRegression(C=.1, penalty='l2', solver='liblinear', class_weight='balanced', max_iter=300, random_state=0)
            m1 = LogisticRegression(C=.1, penalty='l2', solver='liblinear', class_weight='balanced', max_iter=300, random_state=0)
            cache_key = k
            if m0_cache is None: m0_cache = {}
            if cache_key not in m0_cache:
                m0.fit(X0, Y); m0_cache[cache_key] = (m0, [data[files[i]][0] for i in test_ids], [data[files[i]][1] for i in test_ids])
            else:
                m0 = m0_cache[cache_key][0]
            m1.fit(X1, Y)
            for i in test_ids:
                f = files[i]; B, y = data[f]; s = lp.rank01(det_curves[f])
                p0 = m0.predict_proba(B)[:, 1]
                p1 = m1.predict_proba(np.column_stack([B, s]))[:, 1]
                yy = y.astype(float)
                l0 = -(yy*np.log2(np.clip(p0,1e-7,1-1e-7)) + (1-yy)*np.log2(np.clip(1-p0,1e-7,1-1e-7)))
                l1 = -(yy*np.log2(np.clip(p1,1e-7,1-1e-7)) + (1-yy)*np.log2(np.clip(1-p1,1e-7,1-1e-7)))
                cdu = l0.mean() - l1.mean()
                rows.append({'series_id': f, 'fold': k, 'L0_bits': float(l0.mean()), 'L1_bits': float(l1.mean()), 'CDU_bits': float(cdu), 'NCDU': float(cdu/max(l0.mean(),1e-12))})
        R = pd.DataFrame(rows)
        return {'L0_bits': float(R.L0_bits.mean()), 'L1_bits': float(R.L1_bits.mean()), 'CDU_bits': float(R.CDU_bits.mean()), 'NCDU': float(R.NCDU.mean()), 'series': R}
    makers = [
        ("Var96_self", lambda f: var[f]),
        ("Var96_monotonic", lambda f: 100.0 * var[f] + 7.0),
        ("Random", None),
    ]
    rng = np.random.default_rng(0)
    for name, maker in makers:
        if maker is None:
            c = {f: rng.random(len(var[f])) for f in files}
        else:
            c = {f: maker(f) for f in files}
        r = fast_oof(c)
        ctrl.append({"control": name, "L0_bits": r["L0_bits"], "L1_bits": r["L1_bits"],
                     "CDU_bits": r["CDU_bits"], "NCDU": r["NCDU"],
                     "series_count": len(r["series"])})
    for lam in [0.0, 0.1, 0.25, 0.5, 1.0]:
        c = {f: var[f] + lam * labels[f] for f in files}
        r = fast_oof(c)
        ctrl.append({"control": f"AddedSignal_{lam:g}", "L0_bits": r["L0_bits"], "L1_bits": r["L1_bits"],
                     "CDU_bits": r["CDU_bits"], "NCDU": r["NCDU"],
                     "series_count": len(r["series"])})
    cdf = pd.DataFrame(ctrl)
    cdf.to_csv(L2 / "poly_cdu_controls.csv", index=False)
    # Hard gates: controls near zero; added signal monotonic.
    added = cdf[cdf.control.str.startswith("AddedSignal_")].CDU_bits.to_numpy()
    checks = {
        "self_copy_abs_cdu": float(abs(cdf.loc[cdf.control == "Var96_self", "CDU_bits"].iloc[0])),
        "monotonic_copy_abs_cdu": float(abs(cdf.loc[cdf.control == "Var96_monotonic", "CDU_bits"].iloc[0])),
        "random_abs_cdu": float(abs(cdf.loc[cdf.control == "Random", "CDU_bits"].iloc[0])),
        "added_signal_monotonic": bool(np.all(np.diff(added) >= -1e-3)),
    }
    checks["sanity_pass"] = (checks["self_copy_abs_cdu"] <= 0.01 and
                              checks["monotonic_copy_abs_cdu"] <= 0.01 and
                              checks["random_abs_cdu"] <= 0.01 and
                              checks["added_signal_monotonic"])
    (L2 / "poly_cdu_sanity.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
    if not checks["sanity_pass"]:
        raise RuntimeError(f"POLY pilot sanity checks failed: {checks}")
    r = fast_oof(curves)
    ref = pd.read_csv(ROOT / "uni_vuspr.csv").set_index("file")
    basis_ref = pd.read_csv(ROOT / "results" / "basis_vuspr.csv").set_index("file")
    raw = float(ref.loc[files, "POLY"].mean())
    fixed = float(basis_ref.loc[files, "Var-96"].mean())
    out = pd.DataFrame([{
        "detector": "POLY", "pilot_series_count": len(files),
        "raw_vus_mean": raw, "basis_fixed_vus_mean": fixed,
        "L0_bits": r["L0_bits"], "L1_bits": r["L1_bits"],
        "CDU_bits": r["CDU_bits"], "NCDU": r["NCDU"],
        "CDU_series_sd": float(r["series"].CDU_bits.std(ddof=1)),
        "estimator": "3-fold whole-series OOF logistic, rank-normalized scores",
    }])
    out.to_csv(L2 / "poly_cdu.csv", index=False)
    r["series"].to_csv(L2 / "poly_cdu_series.csv", index=False)
    return cdf, checks, out


def main():
    curves, prov = write_pointwise()
    lines = ["# POLY score provenance (Layer-2 pilot)", "", f"- detector: POLY", f"- TSB-AD commit: `{COMMIT}`",
             f"- seed: {SEED}", "- official HP: `{'periodicity': 1, 'power': 4}`", "- scope: 3 R0-passing sequences only", "",
             "| series_id | length | window | finite_ratio | official_vus | reproduced_vus | abs_diff | score_sha256 | label_sha256 |", "|---|---:|---:|---:|---:|---:|---:|---|---|"]
    for p in prov:
        lines.append(f"| {p['series_id']} | {p['length']} | {p['window']} | {p['finite_ratio']:.6f} | {p['official_vus']:.12g} | {p['reproduced_vus']:.12g} | {p['vus_abs_diff']:.3g} | `{p['score_sha256']}` | `{p['label_sha256']}` |")
    (ROOT / "poly_score_provenance.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    cdf, checks, out = run_controls_and_cdu(curves)
    report = ["# POLY Layer-2 CDU pilot", "", "Scope: three sequences that passed strict Gate R0 for POLY. No Sub-PCA or other detector was run. This is an engineering pilot, not a benchmark conclusion.", "", "## Sanity checks", "", "```json", json.dumps(checks, indent=2), "```", "", "## Controls", "", cdf.to_markdown(index=False), "", "## POLY result", "", out.to_markdown(index=False), ""]
    (ROOT / "POLY_LAYER2_PILOT.md").write_text("\n".join(report), encoding="utf-8")
    print(out.to_string(index=False))
    print(cdf.to_string(index=False))


if __name__ == "__main__":
    main()
