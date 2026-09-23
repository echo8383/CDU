"""Review completed secondary-probe outputs and write paper-facing evidence."""
from pathlib import Path
import argparse
import json
import subprocess
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from evaluate_cdu_protocol_v1 import DETECTORS, load_source_map
from run_probe_robustness import CONTROL_NAMES
from run_protocol_v1_controls import atomic_csv, atomic_json

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--training-cap", type=int, default=2048)
    args = parser.parse_args()
    name = "full" if not args.training_cap else f"cap{args.training_cap}"
    folder = ROOT / "protocol_probe_results" / name
    out = ROOT / "paper/evidence/probe_robustness" / name
    out.mkdir(parents=True, exist_ok=True)
    mapping = load_source_map()
    manifest_path = folder / "RUN_MANIFEST.json"
    if not manifest_path.exists():
        print("Secondary probe is queued; no fitted results yet.")
        return
    manifest = json.loads(manifest_path.read_text())
    progress, summaries, controls = [], [], []
    for probe in manifest["probes"]:
        baseline = folder / probe / "baseline"
        for detector in list(CONTROL_NAMES.values()) + list(DETECTORS):
            d = folder / probe / detector
            files = list((d / "by_source").glob("*.csv"))
            status = "INCOMPLETE"
            if (d / "SUMMARY.csv").exists():
                series = pd.read_csv(d / "PER_SERIES.csv").set_index("series_id").sort_index()
                base = pd.read_csv(baseline / "PER_SERIES.csv").set_index("series_id").sort_index()
                assert series.index.is_unique and set(series.index) == set(mapping)
                assert (series.source_dataset == pd.Series(mapping).loc[series.index]).all()
                np.testing.assert_allclose(series.L_basis, base.loc[series.index].L_basis, atol=1e-14, rtol=0)
                np.testing.assert_allclose(series.CDU, series.L_basis-series.L_basis_detector, atol=1e-14, rtol=0)
                assert np.isfinite(series[["L_basis","L_basis_detector","CDU"]]).all().all()
                values = series.groupby("source_dataset").CDU.mean().sort_index().to_numpy()
                assert len(values) == 23
                boot = values[np.random.default_rng(2024).integers(0, 23, (10000, 23))].mean(axis=1)
                lo, hi = np.quantile(boot, [.025, .975])
                row = pd.read_csv(d / "SUMMARY.csv").iloc[0].to_dict()
                assert row["signature"] == manifest["signature"]
                np.testing.assert_allclose([row["CDU"], row["CDU_CI_low"], row["CDU_CI_high"]],
                                           [values.mean(), lo, hi], atol=1e-14, rtol=0)
                warning_folds = 0
                for path in (d / "by_source").glob("*.json"):
                    meta = json.loads(path.read_text())
                    assert meta["test_source"] not in meta["training_sources"]
                    assert meta["signature"] == manifest["signature"]
                    warning_folds += bool(meta["warnings"])
                row["warning_folds"] = warning_folds
                row["training_cap"] = args.training_cap
                if detector in CONTROL_NAMES.values():
                    expected = lo > 0 if detector == "complementary_alpha_2" else lo <= 0 <= hi
                    row["expectation_check"] = "PASS" if expected else "NOT_MET"
                    controls.append(row)
                else:
                    summaries.append(row)
                status = "COMPLETE_VALIDATED"
            progress.append({"probe": probe, "condition": detector, "sources": len(files), "status": status})
    atomic_csv(pd.DataFrame(progress), out / "PROGRESS.csv")
    atomic_csv(pd.DataFrame(summaries), out / "SUMMARY.csv")
    atomic_csv(pd.DataFrame(controls), out / "CONTROLS.csv")
    associations = []
    hgb = pd.DataFrame([r for r in summaries if r["probe"] == "hgb"])
    if len(hgb) == 9:
        hgb = hgb.set_index("detector").loc[list(DETECTORS)]
        full = pd.read_csv(ROOT / "paper/evidence/fast_main/MAIN_RESULTS.csv").set_index("Detector").loc[list(DETECTORS)]
        associations.append({"comparison": "HGB vs primary full-data logistic",
                             "rho": spearmanr(hgb.CDU, full.CDU).statistic,
                             "matched_training_budget": args.training_cap == 0})
        logistic = pd.DataFrame([r for r in summaries if r["probe"] == "logistic"])
        if len(logistic) == 9:
            logistic = logistic.set_index("detector").loc[list(DETECTORS)]
            associations.append({"comparison": "HGB vs matched-budget logistic",
                                 "rho": spearmanr(hgb.CDU, logistic.CDU).statistic,
                                 "matched_training_budget": True})
    atomic_csv(pd.DataFrame(associations), out / "RANK_STABILITY.csv")
    atomic_json(manifest, out / "RUN_MANIFEST.json")
    lines = ["# 第二探针稳健性实验", "",
             f"训练点上限：{'全量' if not args.training_cap else str(args.training_cap) + '/series'}。测试时间点全部保留。",
             "固定 HGB：32 次 boosting，最多 7 个叶子，深度 3，学习率 0.1，最小叶节点 100，L2=1，31 bins。",
             "不启用 early stopping，不使用随机时间点验证，不搜索超参数；23-source LOSO 与原来源宏平均、配对 Bootstrap 相同。",
             "", "| Probe | Condition | Sources | Status |", "|---|---|---:|---|"]
    lines += [f"| {r['probe']} | {r['condition']} | {r['sources']}/23 | {r['status']} |" for r in progress]
    lines += ["", "已完成数据见同目录 SUMMARY.csv 与 CONTROLS.csv；部分折结果不得作为完整总体估计。",
              "若使用训练抽样，matched logistic 采用相同抽样和权重；不能将与全量主结果的差异仅归因于 probe。",
              "控制检查未满足预期时必须报告，不调参数使其转为通过。"]
    (ROOT / "paper/reports/08_probe_robustness.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    # Main-text integration requires the full detector population and controls.
    # Partial results remain in the evidence report and are never used for ranking.
    all_controls = [r for r in controls if r["probe"] == "hgb"]
    if len(hgb) == 9 and len(all_controls) == 3:
        rho = associations[-1]["rho"] if args.training_cap else associations[0]["rho"]
        positive = int((hgb.CDU_CI_low > 0).sum())
        control_ok = all(r["expectation_check"] == "PASS" for r in all_controls)
        budget_en = ("all training points" if not args.training_cap else
                     f"at most {args.training_cap} label-independently sampled training points per series, "
                     "with a matched logistic comparison")
        budget_zh = ("全部训练点" if not args.training_cap else
                     f"每条训练序列最多 {args.training_cap} 个无标签抽样点及匹配的 logistic 对照")
        en = (r"\subsection{Secondary-probe sensitivity}" + "\n"
              "A fixed histogram gradient-boosting probe (32 trees, at most seven leaves per tree; "
              "no early stopping or tuning) uses " + budget_en +
              ", unchanged source-LOSO splits, and all test points. "
              f"Across nine detectors its CDU rank correlation with logistic is {rho:.3f}; "
              f"{positive}/9 source-bootstrap intervals lie above zero. "
              + ("Duplicate/noise intervals include zero and synthetic utility is positive."
                 if control_ok else "At least one control expectation is unmet; this does not establish probe robustness.")
              + "\n")
        zh = (r"\subsection{第二探针敏感性}" + "\n"
              "固定直方图梯度提升探针使用 32 棵树、每棵树最多七个叶子，不启用 early stopping 或调参；采用"
              + budget_zh + "，来源留一划分不变且保留全部测试点。"
              f"九个检测器的 CDU 排名与 logistic 的相关系数为 {rho:.3f}，"
              f"{positive}/9 个来源级 Bootstrap 区间完全高于零。"
              + ("复制和噪声区间包含零，合成效用为正。"
                 if control_ok else "至少一项控制未满足预期，不能据此确立探针稳健性。") + "\n")
        # For a sampled run, do not publish a claim before the matched run completes.
        if not args.training_cap or len([r for r in summaries if r["probe"] == "logistic"]) == 9:
            for filename, content in [("probe_robustness_generated.tex", en),
                                      ("probe_robustness_generated_zh.tex", zh)]:
                (ROOT / "icassp/sections" / filename).write_text(content, encoding="utf-8")
            for build in ["build.ps1", "build_zh.ps1"]:
                result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(ROOT / "icassp" / build)], cwd=ROOT)
                print(f"[paper] {build} exit={result.returncode}", flush=True)
            print("[paper] Secondary-probe section refreshed; final page-layout review still required.", flush=True)
    print(pd.DataFrame(progress).to_string(index=False))


if __name__ == "__main__":
    main()
