# CDU Evaluation Protocol v1

Status: **FROZEN BEFORE SOURCE-GROUPED MAIN RESULTS**  
Freeze date: 2026-08-30  
Random seed: 2024  
Scope: the frozen 350-series TSB-AD-U population, the declared 31-score basis, and the nine Stage-2 audited detector score caches.

This document is the research contract for the ICASSP 2027 submission. Except for a documented implementation bug, choices below must not be changed after inspecting source-grouped outcomes. Any bug fix must retain the original output, state the failure mechanism, add a regression test, and increment the protocol patch version.

## 1. Research question and permitted interpretation

The only primary research question is:

> Given a declared low-complexity statistical basis \(B\), how much additional label-relevant predictive information is provided by a detector score \(S_D\)?

The population target is

\[
\operatorname{CDU}^{*}(D\mid B)=\mathcal R^{*}(B)-\mathcal R^{*}(B,S_D).
\]

Under log-loss and Bayes-optimal prediction,

\[
\operatorname{CDU}^{*}(D\mid B)=I(Y;S_D\mid B).
\]

The operational estimate for a fixed probe family \(\mathcal Q\) is

\[
\widehat{\operatorname{CDU}}_{\mathcal Q}
=\widehat L_{\mathrm{CF}}(B)-\widehat L_{\mathrm{CF}}(B,S_D).
\]

Finite-sample CDU is a **probe-relative operational estimate**. It is not presented as an exact finite-sample estimator of conditional mutual information. Positive CDU supports only the statement that a detector contains held-out label-predictive information not captured by the declared basis and selected probe. It does not establish causal, architectural, or mechanistic attribution.

The paper must not claim that CDU is a replacement for Raw VUS or that it identifies the best detector. The terms *declared low-complexity statistical basis* and *beyond-basis contribution* are used in formal claims; *trivial statistics* may appear only as motivation.

## 2. Frozen data and detector objects

- Benchmark index: `uni_vuspr.csv`, exactly 350 unique TSB-AD-U series.
- Labels: the `label` arrays in `layer2_results/basis_scores/<series_id>.npz`, checked against the benchmark CSV labels.
- Declared basis: the 31 cached point-wise basis columns listed below; no label or detector result was used to select them.
- Detector objects: SubPCA, POLY, MOMENT_FT, MOMENT_ZS, M2N2, TranAD, TimesNet, FITS, and AnomalyTransformer.
- Detector inputs: only the final Stage-2 audited point-wise score caches. Detectors are never rerun by this evaluator.
- Historical leaderboard values are excluded from all protocol-v1 losses.
- The two reproducible AnomalyTransformer collapse series remain in the population. A constant score is rank-normalized to a constant 0.5, never to an artificial time ramp.

### 2.1 Declared 31-score basis

`Var-{8,16,32,64,96,128,256}`; `Range-{8,16,32,64,96,128,256}`; `Last-{1,2,3,8,16,32,64}`; `Centered-{3,16,64}`; `AbsDiff-{1,4,16}`; `MAD-{32,128}`; and `SpecEnt-{64,256}`.

The cached basis representation is the declared representation: its columns were already label-free rank normalized when the cache was created. The evaluator validates its shape, names, finiteness, range, label length, and ordering, but does not attempt to reconstruct unavailable pre-rank raw basis values. Raw detector scores receive per-series average-rank normalization

\[
r_i=(\operatorname{rank}_{\mathrm{average}}(x_i)-0.5)/n.
\]

This explicitly maps a constant detector score to 0.5 and handles other ties without introducing a time ramp. Rank normalization uses scores only and never labels. Applying robust-z to the declared cached representation is a sensitivity setting, not a replacement primary protocol.

The declared basis cache is stored as `float32`; primary probe feature matrices preserve that dtype instead of silently duplicating the full population as `float64`. Rank-normalized detector/control features are cast to the same `float32` representation before concatenation. Losses, probabilities, aggregation, and reported outputs use `float64`. This dtype policy is part of the frozen execution configuration.

### 2.2 Predeclared basis families for sensitivity analysis

- Dispersion: all `Var-*`, `Range-*`, and `MAD-*` columns.
- Lagged level: all `Last-*` columns.
- Local context: all `Centered-*` columns.
- Difference: all `AbsDiff-*` columns.
- Spectral: all `SpecEnt-*` columns.

Sensitivity analyses are full basis, each family alone, and full-basis leave-one-family-out. They may change the magnitude of CDU; the required question is whether qualitative high/near-zero patterns and ranks are robust. CDU is always reported as relative to the declared basis.

## 3. Four prediction conditions

Every held-out series produces four losses on exactly the same timestamps:

| Condition | Features |
|---|---|
| Null | Outer-training anomaly prior only |
| Basis | 31 basis features |
| Detector | The evaluated detector score only |
| Basis + Detector | The same 31 basis features plus that detector score |

All losses are mean binary log-loss in bits, with probabilities clipped only for numerical evaluation to `[1e-7, 1-1e-7]`.

\[
U_B=L_0-L_B,\qquad U_D=L_0-L_D,\qquad \operatorname{CDU}=L_B-L_{B+D}.
\]

`U_D` is the metric-semantics control. Raw VUS remains a separately reported range-aware benchmark metric; detector-only utility and CDU are both computed under the same point-wise held-out log-loss protocol.

## 4. Leakage-safe splitting and hyperparameter selection

### 4.1 Outer evaluation

The primary outer split is leave-one-source-dataset-out. `source_groups.json` is authoritative. Its source key is mechanically extracted from the frozen series ID using `^\d+_([^_]+)_`; labels and scores cannot affect grouping. There are 23 source groups. The semantic `dataset_family` used by the previous hard-subset analysis is not used here.

All series from the held-out source are invisible to fitting and hyperparameter selection. Random whole-series folds may appear only as a secondary sensitivity analysis.

### 4.2 Inner grouped cross-validation

For every outer training set, hyperparameters are chosen only by inner five-fold source-grouped CV. Sorted training source names are permuted once with seed 2024 and divided into five folds with `numpy.array_split`. The same inner folds and search budget are used for Basis, Detector, and Basis+Detector.

Primary probe:

```text
LogisticRegression(
    penalty="l2",
    solver="liblinear",
    class_weight=None,
    max_iter=300,
    random_state=2024
)
C grid = [0.01, 0.1, 1.0, 10.0]
```

Each condition selects its own `C` by minimum inner held-out source-macro log-loss; exact ties choose the smaller `C`. Search spaces, folds, solver, stopping rule, and budget are identical. The only feature difference between Basis and Basis+Detector is the addition of \(S_D\).

The robustness probe is a fixed small HistGradientBoosting model whose exact configuration will be added as protocol v1.1 before its outcomes are inspected. It is not permitted to tune a separate large search space per detector.

## 5. Weighting, aggregation, and uncertainty

No class weighting is used. Training point weights implement equal-source/equal-series risk:

1. each training source has equal total weight;
2. within a source, each series has equal total weight;
3. within a series, each timestamp has equal weight;
4. weights are rescaled to mean one before fitting so `C` has a stable numerical interpretation.

Evaluation first averages timestamp loss within each series, then averages series within each source, then averages sources. This source-macro value is the primary reported result. Series-macro and point-micro are sensitivity aggregations only.

Uncertainty is a paired cluster bootstrap over the 23 held-out source contributions. For each bootstrap replicate, source datasets are sampled with replacement and every paired condition for a sampled source is retained. Use 10,000 replicates and seed 2024. Report percentile 95% intervals and the positive-source fraction

\[
\#\{g:\Delta_g>0\}/\#g,
\quad \Delta_g=L_g(B)-L_g(B,S_D).
\]

Negative finite-sample CDU values are reported without clipping and are not interpreted as negative mutual information.

## 6. Required controls

Before interpreting real detectors, the same source-grouped evaluator must pass:

1. **Redundant score:** `S_dup = B_j`, with the formal exact-duplicate column frozen as `Var-96` (basis index 4), plus a later declared deterministic function of `B`; expected CDU is near the empirical probe/noise floor. The column must not be changed after seeing the control result.
2. **Irrelevant score:** seeded random noise and, later, within-series circularly shifted detector scores; expected CDU is near the empirical probe/noise floor. The formal independent-noise seed is the first 64 bits of SHA-256 over `CDU-protocol-v1|series_id|independent_noise`.
3. **Complementary synthetic score:** the formal calibration is `S_alpha = Z + alpha Y`, where the same per-series deterministic standard-normal `Z` is used for every alpha and `alpha` is frozen to `[0, 0.25, 0.5, 1.0, 2.0]`. Each resulting score receives the primary average-rank transform. This intentionally label-informed score is a calibration instrument, never a detector. Estimated CDU should show a clear overall increase with `alpha`, and the largest alpha should have a source-cluster interval above zero.

Today’s fast duplicate/noise tests are implementation unit tests on synthetic grouped data. They are not paper results. Full 350-series controls must be run under the frozen protocol before a detector claim is accepted.

Formal-control GO requires: duplicate and independent-noise 95% intervals cover zero; neither negative control has an interval strictly above zero; complementary CDU has positive Spearman association with alpha and the largest alpha has a 95% interval above zero; every series is held out exactly once; outer and inner source sets are disjoint; every loss is finite; a checkpoint/resume regression matches a clean calculation; and cached `L_null`/`L_basis` values are bitwise identical across controls. Failure stops the pilot and triggers an implementation audit rather than a favorable protocol change.

## 7. Frozen outputs

Every detector must write one row per held-out series with:

```text
series_id, source_dataset, detector, outer_fold,
L_null, L_basis, L_detector, L_basis_detector,
basis_utility, detector_utility, CDU,
C_basis, C_detector, C_basis_detector,
n_points, protocol_version
```

Aggregate files must retain source-level contributions and selected hyperparameters. Ambiguous fields such as `P(CDU > 0)` are forbidden. Use `positive_source_fraction` and `bootstrap_prob_source_macro_positive` explicitly.

## 8. Claims and decision rules

- If source-grouped rank separation persists, controls are near zero, several source-cluster intervals exclude zero, and probe/basis sensitivity is qualitatively stable, the main claim is beyond-basis rank divergence.
- If ranks persist but intervals are wide, report estimated differences with source-level uncertainty and avoid significance language.
- If outcomes depend strongly on probe or basis, make protocol relativity the result rather than hiding it.
- If source grouping removes the separation, random-series Stage-2 values cannot remain the main evidence; the result becomes a benchmark leakage/domain-transfer audit.

No detector additions, ensemble selection, CDU-guided training, basis redesign, or post-outcome threshold changes are part of protocol v1.

## 9. Provenance and reproducibility

The CDU project directory is not itself a Git worktree. Therefore protocol-v1 provenance is file-hash based. Detector implementation/source commits remain those recorded in `layer2_results/STAGE2_DETECTOR_PROVENANCE.csv`. `source_groups.json`, this document, evaluator code, sanity outputs, and the final environment lock must be included in a SHA-256 manifest before the main run.
