"""Read-only checks for the quantitative claims used by the submission story."""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


ROOT = Path(__file__).resolve().parents[1]
d = pd.read_csv(ROOT / "paper/evidence/rank_probe_extension/DETECTORS.csv")
raw = pd.read_csv(ROOT / "paper/evidence/fast_main/MAIN_RESULTS.csv").set_index("Detector")
decomp = pd.read_csv(ROOT / "paper/evidence/score_decomposition/DETECTOR_DECOMPOSITION_SUMMARY.csv").set_index("detector")
paired = pd.read_csv(ROOT / "paper/evidence/paired_contrasts/PAIRED_CDU_CONTRASTS.csv")
spline = d[d.probe == "spline"].set_index("detector")
standalone = pd.read_csv(ROOT / "paper/evidence/cdu_followup/DETECTOR_ONLY_VS_CDU.csv")
standalone = standalone[standalone.probe == "spline"].set_index("detector")

poly_zs = float(spline.loc["POLY", "CDU"] - spline.loc["MOMENT_ZS", "CDU"])
saved_poly_zs = float(paired.query(
    "probe == 'spline' and detector_A == 'POLY' and detector_B == 'MOMENT_ZS'"
).delta_CDU.iloc[0])
assert abs(poly_zs - 0.005931830033799904) < 1e-14
assert abs(saved_poly_zs - poly_zs) < 1e-14
assert int(raw.Raw_VUS.rank(ascending=False).loc["M2N2"]) == 5
assert int(spline.CDU.rank(ascending=False).loc["M2N2"]) == 2
matched_rho = float(spearmanr(standalone.detector_utility.reindex(spline.index), spline.CDU).statistic)
assert abs(matched_rho - 2 / 3) < 1e-12
assert [int(standalone.detector_utility.rank(ascending=False).loc[name]) for name in
        ("MOMENT_FT", "MOMENT_ZS", "TranAD")] == [4, 5, 6]
assert [int(spline.CDU.rank(ascending=False).loc[name]) for name in
        ("MOMENT_FT", "MOMENT_ZS", "TranAD")] == [7, 9, 4]
assert abs(decomp.loc["MOMENT_ZS", "source_macro_R2"] - 0.904414914249999) < 1e-14

rho = float(spearmanr(decomp.source_macro_R2, spline.CDU.reindex(decomp.index)).statistic)
assert abs(rho + 1 / 6) < 1e-12
top4 = {probe: set(group.nlargest(4, "CDU").detector)
        for probe, group in d.groupby("probe")}
assert len({tuple(sorted(value)) for value in top4.values()}) == 1

seed = pd.read_csv(ROOT / "paper/evidence/cdu_followup/SPLINE_FIVE_SEEDS.csv")
seed_ranks = seed.pivot(index="detector", columns="seed", values="CDU").rank(ascending=False)
assert (seed_ranks.nunique(axis=1) == 1).all()
basis = pd.read_csv(ROOT / "paper/evidence/cdu_followup/SPLINE_BASIS_COMPLETED.csv")
assert basis.rho_vs_full.min() >= 0.9166

controls = pd.read_csv(ROOT / "paper/evidence/rank_probe_extension/CONTROLS.csv")
for probe, group in controls.groupby("probe"):
    negative = group[group.detector.isin(["duplicate_Var96", "independent_noise"])]
    positive = group[group.detector == "complementary_alpha2"]
    assert (negative.CI_low <= 0).all(), probe
    assert (positive.CI_low > 0).all(), probe

reference = pd.read_csv(ROOT / "paper/evidence/reference_robustness/DETECTORS.csv")
stability = pd.read_csv(ROOT / "paper/evidence/reference_robustness/STABILITY.csv")
assert len(reference) == 6 * len(spline)
assert len(stability) == 6
primary_top4 = set(spline.CDU.nlargest(4).index)
for (experiment, variant), group in reference.groupby(["experiment", "variant"]):
    assert set(group.detector) == set(spline.index)
    assert (group.n_series == 350).all() and (group.n_sources == 23).all()
    comparison = stability[(stability.experiment == experiment) & (stability.variant == variant)].iloc[0]
    actual_rho = spearmanr(spline.CDU.reindex(group.detector), group.CDU).statistic
    assert np.isclose(actual_rho, comparison.rho_vs_primary_spline)
    assert (set(group.nlargest(4, "CDU").detector) == primary_top4) == comparison.top4_same
assert int(reference.query("experiment == 'normalization' and variant == 'minmax' and detector == 'POLY'").CDU_rank.iloc[0]) == 9
assert stability.query("experiment == 'normalization' and variant == 'minmax'").top4_same.iloc[0] == False

print("PASS: all headline claims match frozen evidence")
print(f"POLY - MOMENT-ZS spline CDU: {poly_zs:.12f} bits")
print(f"Reconstruction R2 vs spline CDU Spearman: {rho:.6f}")
print(f"Stable top four: {sorted(next(iter(top4.values())))}")
print(f"Matched detector-only/CDU rank Spearman: {matched_rho:.6f}")
print("Reference robustness: 6 complete variants; min-max top-four exception confirmed")
