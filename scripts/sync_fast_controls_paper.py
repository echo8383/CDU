"""Validate completed fixed-C controls and refresh paper evidence; never fit a model.

Incomplete controls are reported only as progress, never as population estimates.
Old nested-CV diagnostics are not inputs to this script.
"""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "protocol_fast_results"
OUT = ROOT / "paper/evidence/fast_controls"
VERSION = "CDU-protocol-fast-v1"
CONTROLS = {
    "duplicate_Var-96": ("Duplicate", "重复基底"),
    "independent_noise": ("Noise", "独立噪声"),
    "complementary_alpha_2": ("Synthetic", "合成分数"),
}
LOSS = ["L_null", "L_basis", "L_detector", "L_basis_detector",
        "basis_utility", "detector_utility", "CDU"]


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


def main():
    mapping = json.loads((ROOT / "source_groups.json").read_text(encoding="utf-8"))["series_to_source"]
    sources = sorted(set(mapping.values()))
    ids = sorted(mapping)
    assert len(ids) == 350 and len(sources) == 23
    base = pd.read_csv(RESULTS / "shared_baseline/PER_SERIES.csv").set_index("series_id")
    assert set(base.index) == set(ids) and base.index.is_unique
    base = base.loc[ids]
    assert (base.protocol_version == VERSION).all()
    draws = np.random.default_rng(2024).integers(0, 23, size=(10000, 23))
    provenance, progress, summaries, series_frames, source_frames, fold_rows = [], [], [], [], [], []

    def read(path):
        provenance.append({"path": path.relative_to(ROOT).as_posix(),
                           "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        return pd.read_csv(path)

    for name in CONTROLS:
        folder = RESULTS / "main" / name
        present = []
        for source in sources:
            path = folder / "by_source" / (source + ".csv")
            meta = path.with_suffix(".json")
            if not path.exists() or not meta.exists():
                continue
            frame = read(path)
            metadata = json.loads(meta.read_text(encoding="utf-8"))
            expected = {sid for sid, group in mapping.items() if group == source}
            assert set(frame.series_id) == expected and frame.series_id.is_unique, (name, source, "IDs")
            assert (frame.source_dataset == source).all() and (frame.outer_fold == source).all()
            assert (frame.detector == name).all() and (frame.protocol_version == VERSION).all()
            assert np.isfinite(frame[LOSS].to_numpy()).all(), (name, source, "finite")
            assert metadata["test_source_id"] == source
            assert set(metadata["training_source_ids"]) == set(sources) - {source}
            assert metadata["fixed_C"] == .1 and metadata["protocol_version"] == VERSION
            indexed = frame.set_index("series_id").sort_index()
            for col in ["L_null", "L_basis", "n_points", "n_anomalies"]:
                np.testing.assert_allclose(indexed[col], base.loc[indexed.index, col], atol=1e-14, rtol=0)
            for col in ["C_basis", "C_detector", "C_basis_detector"]:
                assert (frame[col] == .1).all()
            for result, a, b in [("CDU", "L_basis", "L_basis_detector"),
                                 ("basis_utility", "L_null", "L_basis"),
                                 ("detector_utility", "L_null", "L_detector")]:
                np.testing.assert_allclose(frame[result], frame[a] - frame[b], atol=1e-14, rtol=0)
            present.append(frame)
            fold_rows.append({"control": name, "test_source": source, "n_series": len(frame),
                              "source_exclusion": "PASS", "paired_rows": "PASS",
                              "shared_baseline": "PASS", "finite_loss": "PASS", "fixed_C": .1})
        complete = len(present) == 23 and all((folder / f).is_file() for f in
                                            ["SUMMARY.csv", "PER_SERIES.csv", "PER_SOURCE.csv"])
        progress.append({"control": name, "completed_sources": len(present), "expected_sources": 23,
                         "status": "COMPLETE_VALIDATED" if complete else "INCOMPLETE"})
        if not complete:
            continue
        frame = pd.concat(present, ignore_index=True).set_index("series_id").loc[ids]
        stored = read(folder / "PER_SERIES.csv").set_index("series_id")
        assert stored.index.is_unique and set(stored.index) == set(ids)
        np.testing.assert_allclose(frame[LOSS], stored.loc[ids, LOSS], atol=1e-14, rtol=0)
        source = frame.groupby("source_dataset")[LOSS].mean().sort_index()
        stored_source = read(folder / "PER_SOURCE.csv").set_index("source_dataset").sort_index()
        np.testing.assert_allclose(source[LOSS], stored_source[LOSS], atol=1e-14, rtol=0)
        summary = read(folder / "SUMMARY.csv").iloc[0]
        assert int(summary.n_series) == 350 and int(summary.n_sources) == 23
        boot = source.CDU.to_numpy()[draws].mean(axis=1)
        low, high = np.quantile(boot, [.025, .975])
        mean, prob = float(source.CDU.mean()), float(np.mean(boot > 0))
        np.testing.assert_allclose(
            [mean, low, high, prob],
            [summary.CDU, summary.CDU_CI_low, summary.CDU_CI_high,
             summary.bootstrap_prob_source_macro_positive], atol=1e-14, rtol=0)
        expectation = low <= 0 <= high if name != "complementary_alpha_2" else low > 0
        summaries.append({"control": name, "CDU": mean, "CDU_CI_low": low, "CDU_CI_high": high,
                          "positive_sources": int((source.CDU > 0).sum()),
                          "bootstrap_prob_source_macro_positive": prob,
                          "n_series": 350, "n_sources": 23,
                          "expectation_check": "PASS" if expectation else "NOT_MET",
                          "protocol_version": VERSION})
        frame["control"] = name
        source["control"] = name
        series_frames.append(frame.reset_index())
        source_frames.append(source.reset_index())

    OUT.mkdir(parents=True, exist_ok=True)
    for filename, frame in [
        ("PROGRESS.csv", pd.DataFrame(progress)), ("FORMAL_CONTROL_SUMMARY.csv", pd.DataFrame(summaries)),
        ("FOLD_AUDIT.csv", pd.DataFrame(fold_rows)),
        ("PER_SERIES.csv", pd.concat(series_frames, ignore_index=True) if series_frames else pd.DataFrame()),
        ("PER_SOURCE.csv", pd.concat(source_frames, ignore_index=True) if source_frames else pd.DataFrame()),
    ]:
        write(OUT / filename, frame.to_csv(index=False))

    # Cheap source-influence sensitivity: reaggregate the existing OOF losses.
    # This is not a refit, nonlinear-probe test, or basis ablation.
    main_sources = read(ROOT / "paper/evidence/fast_main/PER_SOURCE.csv")
    main_summary = read(ROOT / "paper/evidence/fast_main/MAIN_RESULTS.csv").set_index("Detector")
    sensitivity = []
    for name, group in main_sources.groupby("detector"):
        assert len(group) == 23 and group.source_dataset.nunique() == 23
        values = group.CDU.to_numpy()
        mean = values.mean()
        np.testing.assert_allclose(mean, main_summary.loc[name, "CDU"], atol=1e-14, rtol=0)
        estimates = (values.sum() - values) / 22
        sensitivity.append({"Detector": name, "CDU": mean, "min_leave_one_source_out": estimates.min(),
                            "max_leave_one_source_out": estimates.max(),
                            "positive_reaggregations": int((estimates > 0).sum()),
                            "n_reaggregations": 23, "probe_refit": False,
                            "sign_stable": bool(np.all(np.sign(estimates) == np.sign(mean)))})
    write(OUT / "SOURCE_INFLUENCE.csv", pd.DataFrame(sensitivity).to_csv(index=False))

    now = datetime.now().astimezone().isoformat()
    write(OUT / "manifest.json", json.dumps({"as_of": now, "sources": provenance,
          "scope": "Control fold/output validation and offline source-influence reaggregation; no refitting"},
          indent=2))
    by_name = {row["control"]: row for row in summaries}
    # Compact, fixed three-row display keeps the 4-page manuscript stable.
    # Units 10^-3 bits keep small control values readable without changing units silently.
    en = [r"Matching fixed-$C$ controls use the same population and baseline.",
          r"CDU [95\% CI], in $10^{-3}$ bits:"]
    zh = [r"匹配的固定 $C$ 控制使用相同总体与基线。",
          r"CDU [95\% CI]，单位为 $10^{-3}$ 比特："]
    for name, (english, chinese) in CONTROLS.items():
        if name in by_name:
            row = by_name[name]
            cells = "$" + f"{row['CDU']*1000:.4f}$ " + "$" + f"[{row['CDU_CI_low']*1000:.4f},{row['CDU_CI_high']*1000:.4f}]$"
        else:
            cells = r"\textemdash"
        en.append(english + " " + cells + ";")
        zh.append(chinese + " " + cells + "；")
    all_complete = len(summaries) == 3
    if all_complete:
        negative_ok = all(by_name[n]["expectation_check"] == "PASS" for n in list(CONTROLS)[:2])
        synthetic_ok = by_name["complementary_alpha_2"]["expectation_check"] == "PASS"
        if negative_ok and synthetic_ok:
            en.append("Duplicate and noise intervals include zero; injected label information produces positive utility. This is calibration, not a real detector or a dose-response test.")
            zh.append("复制与噪声区间包含零；注入标签信息产生正效用。这是校准，不是真实检测器结果或剂量响应检验。")
        else:
            en.append("At least one diagnostic expectation is not met; these results do not establish protocol qualification. No scores were tuned or excluded.")
            zh.append("至少一项诊断未满足预期，不能据此宣称协议通过验收；没有据此调整分数或排除检测器。")
    else:
        en.append("dashes denote unfinished controls. No full acceptance is claimed; nested-CV controls are not substitutes.")
        zh.append("横线表示尚未完成，并非零值。不声称完整诊断已通过；早期嵌套交叉验证控制不能替代当前控制。")
    write(ROOT / "icassp/sections/fast_controls_generated.tex", "\n".join(en) + "\n")
    write(ROOT / "icassp/sections/fast_controls_generated_zh.tex", "\n".join(zh) + "\n")

    report = ["# Fast controls and paper synchronization", "", f"Updated: {now}", "",
              "Nine detector primary runs are reused; detector training and primary probes were not rerun.",
              "", "| Control | Sources | Status |", "|---|---:|---|"]
    report += [f"| {r['control']} | {r['completed_sources']}/23 | {r['status']} |" for r in progress]
    report += ["", "| Control | CDU (bits) | 95% CI | Diagnostic expectation |",
               "|---|---:|---|---|"]
    report += [f"| {r['control']} | {r['CDU']:.12g} | [{r['CDU_CI_low']:.12g}, {r['CDU_CI_high']:.12g}] | {r['expectation_check']} |" for r in summaries]
    report += ["", "Checks: expected series IDs per source; 350 unique series; finite losses; fixed C=0.1; "
               "held-out source absent from training; shared L0/LB and time-point counts; per-series CDU=L_B-L_BD; "
               "23-source macro means; independently regenerated 10,000-replicate paired bootstrap.",
               "", "Source influence is reaggregation of existing OOF losses without fitting new probes. "
               "It is not evidence of robustness to different probe families or basis definitions.",
               "", "Remaining nonlinear-probe and basis-family experiments have not been executed. "
               "They require an explicit separate fixed configuration and their own controls; no results are invented.",
               "", "The old QUEUE_STATUS.json is not a global completion signal: use the control-specific "
               "350-series summary and by-source files."]
    write(ROOT / "paper/reports/07_controls_latest.md", "\n".join(report) + "\n")
    write(OUT / "CONTROL_ACCEPTANCE.md", "\n".join(report) + "\n")
    print(pd.DataFrame(progress).to_string(index=False), flush=True)
    if summaries:
        print(pd.DataFrame(summaries).to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
