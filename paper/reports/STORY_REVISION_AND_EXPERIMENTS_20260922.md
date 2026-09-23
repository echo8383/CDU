# Story-first revision and supplementary experiments

## Central claim

The manuscript now has one organizing statement:

> Standard TSAD benchmarks measure whether a detector score predicts anomalies;
> they do not measure what the score adds beyond simple statistical signals.
> CDU makes that missing contribution measurable.

All method, result, and robustness material is subordinated to three findings:

1. standalone performance and added utility are different;
2. the conditional comparison is stable across probes, sampling seeds, and reference perturbations;
3. statistical reconstructibility is not the same as additional label utility.

## Adopted manuscript changes

- Replaced the defensive title with a benchmark-blind-spot title.
- Rewrote the abstract and first introduction paragraph around the missing evaluation question.
- Moved the POLY--MOMENT contrast and MOMENT-ZS reconstruction result to page 1.
- Recast contributions as outcomes rather than engineering steps.
- Uses *statistical reference* in the narrative; $B$ remains the mathematical basis symbol.
- Keeps the conditional-mutual-information identity as legitimacy, not as a claim to invent CMI.
- Makes spline logistic the primary probe and linear/HGB robustness probes.
- Compresses the feature inventory and full-data linear discussion.
- Reorganizes the Results headings so their sequence states the paper's claim.
- Retains matched-metric $U_D$, which isolates conditioning from a VUS/log-loss metric change.
- Moves tiny control exceptions and detector-wise multiplicity details out of the four-page story while preserving them in the technical evidence report.
- Rewrites the conclusion as a direct implication followed by one concentrated scope sentence.
- Redesigns the main table to five centered columns and strengthens the three-panel result figure with direct labels and conclusion-style panel titles.

## Structural revision on 2026-09-23

The abstract and introduction now distinguish the VUS/CDU example from the matched-log-loss $U_D$/CDU comparison. Figure 2a directly plots the matched comparison ($\rho=0.667$), and Table 1 gives $U_D$ ranks. Results follow three findings in figure order---standalone versus added utility, score reconstructibility versus added label utility, and reproducibility---then controls. The common rank interface is stated as an evaluation choice about within-series ordering. The min-max sensitivity remains reported and is interpreted as a change in score interface. The conclusion ends on the empirical implication. No new experiment was launched for this revision.

## Existing high-return experiment already complete

The requested all-detector score-reconstruction analysis was already complete for all nine frozen detectors. `DETECTOR_DECOMPOSITION_SUMMARY.csv` contains 350 series and 23 sources for every detector. The headline contrast is:

- MOMENT-ZS: source-macro reconstruction $R^2=0.904$, Spearman $=0.951$;
- M2N2: $R^2=0.054$, Spearman $=0.217$;
- TranAD: $R^2=-0.002$, Spearman $=0.082$.

Across all nine detectors, reconstruction $R^2$ and primary spline CDU have Spearman correlation $-0.167$. The complete nine-point view is Figure 2b.

## New offline experiments

No detector is rerun. Both branches read frozen point-wise caches and use the same 23-source leave-one-source-out spline protocol, deterministic training sample, source/series weighting, complete test curves, and source-cluster aggregation as the primary analysis.

### Score-interface normalization

The primary rank interface is compared with two label-free within-series maps:

- min-max scaling;
- Gaussianized z-score, $\Phi((s-\bar s)/\sigma_s)$.

The ranked 31-feature reference is unchanged, so this specifically tests whether detector ordering is an artifact of how heterogeneous detector-score scales enter the probe. Outputs are under `protocol_reference_robustness/normalization/cap2048/`.

### Statistical-reference strength

The ranked detector interface is fixed while the reference grows cumulatively:

1. variance (7 features);
2. variance + range (14);
3. plus next-point and centered deviations (24);
4. plus absolute differences and MAD (29);
5. full reference, adding spectral entropy (31; existing primary result).

This tests whether CDU changes coherently as the conditioning question becomes harder. Outputs are under `protocol_reference_robustness/strength/cap2048/`.

Both runners checkpoint every held-out source and resume after interruption. All six variants are now complete, with consolidated evidence in `paper/evidence/reference_robustness/DETECTORS.csv` and `STABILITY.csv`. The result and its material min-max exception are documented in [REFERENCE_ROBUSTNESS_20260923.md](REFERENCE_ROBUSTNESS_20260923.md). The main manuscript now reports these findings in the robustness paragraph and conclusion.

## Commands

```powershell
./scripts/show_reference_robustness_progress.ps1
python scripts/summarize_reference_robustness.py
```

All variants have all nine detector summaries. The frozen primary numbers are unchanged.
