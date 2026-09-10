# CDU project: architecture, evidence ledger, and execution plan

> Living technical record. This document consolidates the project as of 2026-09-08. It distinguishes historical/pinned Stage-2 outputs from the not-yet-complete Protocol v1 main results. It is not permission to change any frozen protocol choice after inspecting outcomes.

## 1. One-sentence project definition

The project evaluates whether a time-series anomaly detector score contributes **held-out, label-relevant predictive information beyond a predeclared low-complexity statistical basis**, rather than evaluating detectors only by their standalone range-aware benchmark VUS.

The formal research question is:

> Given a declared low-complexity statistical basis \(B\), how much additional label-relevant predictive information is provided by a detector score \(S_D\)?

The project does **not** attempt to prove that a particular architecture causally understands anomalies, that CDU replaces Raw VUS, or that the detector with the highest CDU is universally the best detector.

## 2. Core idea: beyond-basis contribution

Traditional TSAD benchmark reporting asks how strongly a detector score aligns with anomaly labels under a metric such as VUS-PR. This is useful but cannot distinguish between:

- a detector that largely reproduces simple local statistics; and
- a detector that adds label-relevant structure not already available from simple statistics.

CDU treats a detector score as an additional feature for a fixed held-out prediction task. Let \(Y\) be the point-wise anomaly label, \(B\) the 31-dimensional declared basis, and \(S_D\) one detector's point-wise score. The population target is:

\[
\operatorname{CDU}^{*}(D\mid B)
= \mathcal R^{*}(B)-\mathcal R^{*}(B,S_D).
\]

Under log-loss with a Bayes-optimal predictor, this equals \(I(Y;S_D\mid B)\). In finite data, the project estimates a **probe-relative operational quantity**, not exact conditional mutual information:

\[
\widehat{\operatorname{CDU}}_{\mathcal Q}
=\widehat L_{\mathrm{CF}}(B)-\widehat L_{\mathrm{CF}}(B,S_D),
\]

where \(\mathcal Q\) is a frozen probe family and \(\widehat L_{\mathrm{CF}}\) is cross-fitted held-out log-loss.

Interpretation:

- Positive CDU: under the declared basis and frozen probe, the detector improves held-out label prediction.
- CDU near zero: no detectable positive conditional increment; the detector may be redundant with the basis or its distinct information may not be usable by this probe.
- Negative finite-sample CDU: adding the score worsens held-out predictive loss in this finite protocol. It is reported without clipping and is **not** interpreted as negative mutual information.

## 3. Frozen data assets

### 3.1 Benchmark population

- Population: exactly 350 TSB-AD-U univariate series.
- Benchmark index: `uni_vuspr.csv`.
- Raw data: `Datasets/TSB-AD-U/`.
- Labels: checked against the label arrays inside the corresponding basis cache.
- Seed policy: 2024 unless a file documents a different historical audit seed.

No series is deleted for poor detector behavior. In particular, the two AnomalyTransformer collapsed-score series remain in the benchmark population.

### 3.2 Declared low-complexity statistical basis

The basis has 31 predeclared point-wise score columns, cached in:

```text
layer2_results/basis_scores/<series_id>.csv.npz
```

The 31 columns are:

```text
Var-{8,16,32,64,96,128,256}
Range-{8,16,32,64,96,128,256}
Last-{1,2,3,8,16,32,64}
Centered-{3,16,64}
AbsDiff-{1,4,16}
MAD-{32,128}
SpecEnt-{64,256}
```

The cached basis representation is already label-free rank normalized. Protocol v1 validates its dimensions, ordering, labels, finite values, and numeric range; it does not silently reconstruct unavailable pre-rank curves.

Predeclared sensitivity families are:

| Family | Basis members |
|---|---|
| Dispersion | `Var-*`, `Range-*`, `MAD-*` |
| Lagged level | `Last-*` |
| Local context | `Centered-*` |
| Difference | `AbsDiff-*` |
| Spectral | `SpecEnt-*` |

### 3.3 Natural trivial-hard data (prepared, not part of Protocol v1 primary endpoint)

This is a separate, completed data-preparation stream. It defines how well the declared basis solves each series without using any detector score to define difficulty.

- 5-fold and 10-fold whole-series cross-fitted basis solvability were prepared.
- 5/10-fold solvability Spearman correlation: 0.969006.
- Hard-set Jaccard: Hard-20 0.892, Hard-30 0.842, Hard-50 0.923.
- Global Hard-20/30/50 sizes: 70 / 105 / 175.
- Family-Hard-20/30 sizes: 80 / 116.
- Global Hard-20 is strongly source/family confounded: UCR accounts for 46/70 (65.7%).

The recommended future primary hard-condition analysis is Family-Hard-20/30, with global Hard subsets only as sensitivity analyses. This stream is intentionally paused: it is not being used to redefine CDU or to select detectors.

Relevant files:

```text
data/trivial_difficulty_5fold.csv
data/trivial_difficulty_10fold.csv
data/trivial_difficulty_groups.csv
data/trivial_difficulty_family_composition.csv
data/trivial_difficulty_family_balanced.csv
data/anomaly_event_basis_metadata.parquet
TRIVIAL_HARD_DATA_AUDIT.md
TRIVIAL_HARD_DATA_REPORT.md
```

## 4. Detector layer: frozen point-wise score objects

The current detector pool is frozen at nine representative definitions:

| Detector | Stage-2 cache location | Current special status |
|---|---|---|
| SubPCA | `layer2_results/detector_scores/SubPCA/` | audited PASS |
| POLY | `layer2_results/poly_pinned_scores/` | audited PASS; pinned historical-compatible implementation |
| MOMENT_FT | `layer2_results/detector_scores/MOMENT_FT/` | audited PASS |
| MOMENT_ZS | `layer2_results/detector_scores/MOMENT_ZS/` | audited PASS |
| M2N2 | `layer2_results/detector_scores/M2N2/` | audited PASS |
| TranAD | `layer2_results/detector_scores/TranAD/` | audited PASS |
| TimesNet | `layer2_results/detector_scores/TimesNet/` | PASS_WITH_NO_POSITIVE_INCREMENT under Stage 2 |
| FITS | `layer2_results/detector_scores/FITS/` | audited PASS |
| AnomalyTransformer | `layer2_results/detector_scores/AnomalyTransformer/` | PASS_WITH_REPRODUCIBLE_COLLAPSE |

All detector caches contain point-wise anomaly scores. A Protocol v1 evaluator reads them but **never reruns a detector**. The same cached curve is the sole input for each detector's future `L_D` and `L_{B+D}` calculations.

### 4.1 Score integrity contract

The Stage-2 cache audit established or documented the following requirements:

- exactly one cached test score per benchmark series;
- score length equals test-label length;
- finite values only;
- score hash and seed/config provenance recorded;
- point order, labels, basis rows, and detector score rows aligned;
- no silent train/test concatenation, padding, timestamp drop, or score reversal;
- cached score is reused consistently for Raw VUS and CDU.

Detector-specific provenance, configuration, implementation, and cache paths are recorded in:

```text
layer2_results/STAGE2_DETECTOR_PROVENANCE.csv
DETECTOR_ENVIRONMENT_LOCK.md
layer2_results/<Detector>_score_manifest.csv
configs/
wrappers/
```

### 4.2 Known exceptions and their disposition

**POLY.** Historical leaderboard parity was investigated separately. The official merged leaderboard used a pre-normalization implementation; a pinned `official_historical` implementation is used for the project cache. Historical leaderboard values are provenance evidence only and must not be mixed into current detector/CDU results. A separate Raw VUS discrepancy was resolved: `0.422519...` came from incorrectly selecting VUS window from a score curve; the correct pinned Raw VUS uses the raw input to select the evaluation window. See `POLY_RAW_VUS_DISCREPANCY_AUDIT.md`.

**AnomalyTransformer.** Two score curves are exactly zero and reproducible:

```text
531_SMAP_id_1_Sensor_tr_1811_1st_4510.csv
536_SMAP_id_6_Sensor_tr_2160_1st_5600.csv
```

They are not NaN/Inf, alignment, score-direction, or cache-hash errors. They are retained. Protocol v1 maps constant detector scores to 0.5 after rank normalization, rather than generating an artificial time ramp.

**TimesNet.** The old ambiguous field `P(CDU > 0)=0.4914` means the per-series positive CDU fraction, not bootstrap probability that macro CDU is positive. The corrected fields are `positive_series_ratio` and `bootstrap_prob_macro_positive`. Its legacy Stage-2 CDU was stably negative; this is not an estimator-bug conclusion and is not a claim of negative mutual information.

## 5. Stage-1 and Stage-2 work already completed

### 5.1 Stage 1: basis characterization and difficulty preparation

Completed tasks:

- generated/cached 31 basis score curves;
- calculated basis VUS and basis metadata;
- prepared leakage-safe trivial-solvability difficulty scores;
- created global and family-balanced hard subsets;
- checked family composition and stability.

Stage 1 is an **evaluation reference**, not a deployable anomaly detector and not a basis selected after looking at detector outcomes.

### 5.2 Stage 2: pinned-cache detector audit and legacy CDU

Completed tasks:

- integrated nine detector wrappers/caches;
- generated 350 point-wise cached scores per detector;
- performed reproducibility, cache-integrity, Raw VUS, alignment, provenance, and CDU consistency checks;
- corrected ambiguous statistical field names;
- audited POLY provenance and AnomalyTransformer collapse;
- froze the Stage-2 detector pool.

The principal Stage-2 audit report is:

```text
STAGE2_FULL_AUDIT_REPORT.md
layer2_results/STAGE2_AUDITED_LEADERBOARD.csv
```

### 5.3 Stage-2 result ledger: historical pinned-cache result, not Protocol v1 result

The following values are preserved because they are useful engineering and exploratory evidence. They were obtained under the older whole-series 5/10-fold CDU protocol and must **not** be used as the eventual Protocol v1 paper table.

| Detector | Stage-2 audited Raw VUS | Stage-2 CDU 5-fold bits | Stage-2 CDU 10-fold bits | Stage-2 status |
|---|---:|---:|---:|---|
| SubPCA | 0.422413 | 0.059996 | 0.061626 | PASS |
| POLY | 0.389271 | 0.008503 | 0.008472 | PASS |
| MOMENT_FT | 0.386409 | 0.001894 | 0.001476 | PASS |
| MOMENT_ZS | 0.383229 | 0.000324 | 0.000245 | PASS |
| M2N2 | 0.287047 | 0.029404 | 0.029511 | PASS |
| TranAD | 0.275403 | 0.021713 | 0.022082 | PASS |
| TimesNet | 0.262746 | -0.000269 | -0.000202 | PASS_WITH_NO_POSITIVE_INCREMENT |
| FITS | 0.246369 | 0.000671 | 0.000483 | PASS |
| AnomalyTransformer | 0.111769 | -0.000200 | -0.000114 | PASS_WITH_REPRODUCIBLE_COLLAPSE |

Source: `STAGE2_FULL_AUDIT_REPORT.md`. These values are cache-only audit values with the relevant Stage-2 Raw VUS window logic; they are not historical leaderboard numbers.

#### Important stale-summary warning

`NINE_DETECTOR_LEADERBOARD.md` contains several earlier Raw VUS values that differ from the final Stage-2 cache-only audit for M2N2, TranAD, TimesNet, and FITS. It is a historical summary, not the source of truth. Do not merge it into any new table without explicitly resolving the source. For Stage 2, cite `STAGE2_FULL_AUDIT_REPORT.md`; for primary paper claims, wait for Protocol v1 results.

### 5.4 What Stage 2 established, and what it did not

Stage 2 established that detector cache outputs can be traced, aligned, and evaluated reproducibly under its frozen pinned execution setting. It did **not** establish a source-held-out, source-macro CDU result. In particular, its whole-series 5/10-fold splits can allow sibling series from the same source to appear in both train and test folds.

## 6. Why Protocol v1 exists

Protocol v1 is not a rerun of detector training and does not invalidate Stage 2. It answers a stricter question:

> Does the reported conditional contribution generalize to an unseen source dataset, rather than exploiting similarity between train and test series from the same source?

The protocol was frozen before source-grouped main outcomes were inspected. Its full contract is in `protocol_v1.md`.

### 6.1 Old and new evaluation designs

| Aspect | Stage 2 legacy CDU | Protocol v1 primary CDU |
|---|---|---|
| Outer split | whole-series 5/10-fold | 23-source leave-one-source-out (LOSO) |
| Can a source appear in train and test? | yes, via different series | no |
| Hyperparameter selection | legacy fixed/whole-series configuration | inner source-grouped 5-fold within outer train |
| Risk weighting | primarily series-level macro | source → series → timestamp equal weighting |
| Main uncertainty unit | series-level bootstrap | paired source-cluster bootstrap |
| Detector output | cached point score | same cached point score |
| Primary losses saved | legacy M0/M1 loss deltas | all \(L_0,L_B,L_D,L_{B+D}\) |
| Constant detector score | legacy behavior | constant mapped to 0.5 |
| Rank ties | legacy behavior | average-rank rule |

### 6.2 Outer source-grouped LOSO

`source_groups.json` maps every series to a source by a mechanically extracted series-ID key (`^\d+_([^_]+)_`). There are 23 groups.

For outer fold \(g\):

```text
outer test  = all series from source g
outer train = all series from the other 22 sources
```

The held-out source cannot influence fitting, `C` selection, preprocessing choices, null-prior estimation, feature selection, or aggregation choices. Its labels are used only to score final held-out predictions.

### 6.3 Inner grouped cross-validation

For each outer training set, sorted training sources are deterministically permuted with seed 2024 and partitioned into five source-grouped inner folds with `numpy.array_split`.

For each of the four `C` values (`0.01, 0.1, 1.0, 10.0`):

```text
fit on inner-train sources
evaluate on inner-validation sources
aggregate validation loss source-macro
```

The condition-specific winning `C` is the one with lowest inner validation loss, with smaller `C` used to break exact ties. The selected probe is then refit on all outer-train sources and evaluated once on the outer-test source.

### 6.4 Probe family

Primary probe:

```python
LogisticRegression(
    penalty="l2",
    solver="liblinear",
    class_weight=None,
    max_iter=300,
    random_state=2024,
)
# C grid: [0.01, 0.1, 1.0, 10.0]
```

No class weights are used because the primary output must preserve an interpretable probability/log-loss target. All conditions have the same solver, grid, search budget, folds, stopping criteria, and seed.

The future nonlinear robustness probe is a fixed small HistGradientBoosting configuration. It must be specified in a protocol patch before outcomes are inspected; it must not receive a detector-specific tuning budget.

### 6.5 Feature preprocessing

Basis features are cached rank-normalized `float32` values. Detector/control scores are normalized per series by average rank:

\[
r_i=(\operatorname{rank}_{\mathrm{average}}(x_i)-0.5)/n.
\]

This transformation uses score values only, not labels. A constant curve becomes a constant 0.5. Feature matrices stay `float32`; probabilities, losses, aggregation, and reports are `float64`.

### 6.6 Four loss conditions and derived quantities

Every held-out timestamp contributes to four predictions, all on the same score/label/time index:

| Name | Features | Role |
|---|---|---|
| \(L_0\) / Null | outer-training anomaly prevalence only | no-feature reference |
| \(L_B\) / Basis | 31 basis features | baseline information available without evaluated detector |
| \(L_D\) / Detector | detector score only | detector-only predictive utility control |
| \(L_{B+D}\) / Basis + Detector | 31 basis features plus detector score | conditional comparison |

Derived quantities are:

\[
U_B=L_0-L_B,
\qquad
U_D=L_0-L_D,
\qquad
\operatorname{CDU}=L_B-L_{B+D}.
\]

`U_D` is essential: it compares standalone detector and conditional utility under the **same** log-loss semantics, rather than comparing a range-aware Raw VUS with CDU and attributing any rank shift entirely to conditioning.

### 6.7 Weighting and source-macro aggregation

Training weights give every source equal total weight; within each source, every series equal total weight; within each series, every timestamp equal total weight. Weights are rescaled to mean one before fitting.

Evaluation is hierarchical:

\[
L_i=\frac{1}{T_i}\sum_t \ell(y_{it},\hat p_{it}),
\qquad
L_g=\frac{1}{|I_g|}\sum_{i\in I_g} L_i,
\qquad
L=\frac{1}{23}\sum_g L_g.
\]

This prevents long series or sources with many series from dominating results. Series-macro and point-micro are sensitivity aggregations, not primary endpoints.

### 6.8 Uncertainty

The primary interval is a paired cluster bootstrap over the 23 held-out source contributions. For each source:

\[
\Delta_g=L_g(B)-L_g(B,S_D).
\]

Bootstrap samples source datasets with replacement and retains both paired losses whenever a source is sampled. The protocol uses 10,000 replicates and seed 2024. It reports:

- 95% percentile interval;
- `positive_source_fraction` = fraction of 23 sources with \(\Delta_g>0\);
- `bootstrap_prob_source_macro_positive` = fraction of bootstrap macro means above zero.

Those two positive quantities must never be labelled by ambiguous text such as `P(CDU > 0)`.

## 7. Formal control program: validating the measurement instrument

Before interpreting any real detector under Protocol v1, the identical evaluator must behave sensibly on three predeclared controls.

| Control | Construction | Expected behavior | Why it matters |
|---|---|---|---|
| Exact duplicate | \(S_{dup}=B_{\text{Var-96}}\) | CDU near zero; CI covers zero | A redundant feature should not be rewarded as new information |
| Independent noise | deterministic per-series random score independent of \(B,Y\) | CDU near zero; CI covers zero | Noise should not receive apparent utility from leakage/overfit |
| Complementary synthetic | \(S_\alpha=Z+\alpha Y\), \(\alpha\in\{0,.25,.5,1,2\}\) | overall CDU rises with \(\alpha\); largest alpha CI above zero | The evaluator must detect known added label information |

The complementary score deliberately contains \(Y\); it is an evaluator calibration object, never a valid detector and never a leaderboard entry.

### 7.1 Formal control GO gate

The main detector run is blocked until all of the following pass:

1. duplicate 95% CI includes zero;
2. independent-noise 95% CI includes zero;
3. neither negative control has a CI strictly above zero;
4. complementary CDU has positive Spearman association with \(\alpha\);
5. largest-alpha complementary interval is above zero;
6. every series is outer-tested exactly once;
7. outer and inner source sets are disjoint;
8. all losses are finite;
9. checkpoint/resume calculation matches a clean calculation;
10. cached `L0` and `LB` are bitwise identical across controls.

If a control fails, the response is an implementation audit and a documented protocol patch—not a result-driven alteration of the basis, split, threshold, or detector set.

## 8. Current execution state (snapshot: 2026-09-08)

### 8.1 Completed

- Protocol contract frozen: `protocol_v1.md`.
- Source grouping frozen: `source_groups.json`, 23 groups.
- Input/hash manifest prepared: `protocol_v1_input_manifest.json`.
- Outer/inner fold audit prepared: `protocol_v1_results/controls/FOLD_AUDIT.csv`.
- Shared detector-independent baseline `L0/LB`: **23/23 outer sources complete**.
- Baseline cache: `protocol_v1_results/controls/shared_baseline/`.

### 8.2 In progress

- Formal exact-duplicate control, `S_dup = Var-96`.
- At the snapshot time, `13/23` source checkpoints were complete.
- The control queue and its Python worker were running; source-level checkpoints make this resumable.

### 8.3 Not yet complete

- independent-noise control;
- complementary synthetic alpha grid;
- clean-versus-resume regression;
- final `CONTROL_ACCEPTANCE.md` GO/STOP decision;
- three-detector Protocol v1 pilot;
- Protocol v1 nine-detector main run;
- robustness probe and basis sensitivity.

An old `CONTROL_ACCEPTANCE.md` may say `STOP / INCOMPLETE`; it reflects the earlier interrupted queue, not a final failure. The final acceptance report is authoritative only after all required controls finish.

### 8.4 Resumability and running commands

The control runner checkpoints after each completed outer source. It guards against incompatible inputs/configuration with:

```text
protocol_v1_results/controls/RUN_SIGNATURE.json
```

Primary scripts:

```text
scripts/evaluate_cdu_protocol_v1.py
scripts/run_protocol_v1_controls.py
scripts/run_protocol_v1_control_queue.ps1
scripts/verify_protocol_v1_resume_clean.py
```

To resume the remaining control queue from project root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_protocol_v1_control_queue.ps1 -BaselinePid 0
```

The queue verifies that shared baseline output exists, resumes the negative controls, runs complementary controls, verifies clean-vs-resume consistency, and then writes acceptance. It does not run a detector or launch a pilot.

## 9. Execution architecture

```text
Raw TSB-AD-U CSV + labels
        │
        ├── 31 basis curves (cached; frozen)
        │       └── B: (T, 31) label-free feature matrix
        │
        ├── 9 detector score caches (cached; frozen)
        │       └── S_D: (T,) point-wise anomaly score
        │
        └── source_groups.json (23 groups)
                │
                ▼
      Protocol v1 outer LOSO source split
                │
                ├── shared evaluator: L0 and LB, cached once
                │
                └── detector/control evaluator:
                        LD and LBD
                        ↓
                        per-series results
                        ↓
                        per-source source-macro results
                        ↓
                        paired source-cluster bootstrap
                        ↓
                        Raw VUS + U_D + CDU table
```

### 9.1 Required output granularity

For each detector, Protocol v1 must save series-level rows with:

```text
series_id
source_dataset
detector
outer_fold
L_null
L_basis
L_detector
L_basis_detector
basis_utility
detector_utility
CDU
C_basis
C_detector
C_basis_detector
n_points
protocol_version
```

Source-level rows, selected hyperparameters, and global summaries must also be retained. Saving only a final mean is insufficient for confidence intervals, heterogeneity analysis, or reproducibility audit.

## 10. Planned execution sequence after controls

### Phase B: three-detector implementation pilot

The pilot detector set is fixed for diagnostic coverage:

| Detector | Why it is included |
|---|---|
| AnomalyTransformer | verifies constant-score/collapse handling and tie normalization |
| MOMENT_ZS | tests whether old near-zero CDU remains near the control floor |
| M2N2 | tests a prior Raw/CDU rank reversal under source-held-out evaluation |

Pilot acceptance checks implementation invariants, not a preferred ranking:

- for constant detector score, \(L_D\approx L_0\) and \(L_{B+D}\approx L_B\);
- `L0` and `LB` must be exactly shared across detectors for the same held-out source;
- all four losses must use identical timestamps, labels, folds, and aggregation weights;
- no detector score may cause silent row dropping, padding, or failed feature construction;
- selected hyperparameters and training/validation source IDs must be logged.

If the pilot exposes a real implementation bug, stop, document the fault, increment the protocol patch version, rerun formal controls, and rerun completed Protocol v1 detector outputs. Do not mix pre- and post-patch results.

### Phase C: main-run manifest freeze

After a passing pilot, write `protocol_v1_mainrun_manifest.json` containing:

- evaluator SHA-256;
- protocol and source-map SHA-256;
- basis manifest hash;
- each detector score-cache hash;
- outer and inner split hashes;
- Python and core dependency versions;
- probe grid and feature-preprocessing configuration;
- random-seed policy.

The resume mechanism must reject checkpoints whose code, configuration, or input hashes do not match this manifest.

### Phase D: nine-detector primary experiment

Run the source-grouped evaluator independently over each cached detector score. No detector is retrained or rescored. The only detector-specific calculations are `LD`, `LBD`, `U_D`, and CDU.

The primary final table should include:

| Detector | Benchmark Raw VUS | Source-macro Raw VUS | \(U_D\) | CDU | 95% source CI | Raw rank | \(U_D\) rank | CDU rank | Positive sources |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|

Two Raw VUS aggregations are needed:

- benchmark-standard Raw VUS for external comparability;
- source-macro Raw VUS as an aggregation-matched control for CDU.

The key paper comparison is not only Raw VUS versus CDU. It is whether detector-only log-loss utility \(U_D\) and conditional utility CDU diverge under the same source-grouped, cross-fitted, source-macro protocol.

### Phase E: robustness, only after primary results freeze

1. Fixed small nonlinear probe, after its configuration is frozen in a protocol patch and its duplicate/noise controls pass.
2. Basis sensitivity: full basis, one family at a time, and leave-one-family-out.
3. Score-normalization sensitivity: robust-z or other predeclared label-free setting.
4. Aggregation sensitivity: series-macro and point-micro.
5. Random whole-series split as a secondary comparison with the old Stage-2 style protocol.

No new detector, ensemble-selection extension, CDU-guided training, basis redesign, post-outcome threshold change, or hard-subset claim is allowed before primary Protocol v1 results are frozen.

## 11. Paper concept and allowed claims

### 11.1 Working contribution statement

1. Formalize beyond-basis detector evaluation as conditional predictive utility, whose population log-loss target corresponds to conditional mutual information.
2. Provide a source-grouped, cross-fitted protocol using a declared low-complexity statistical basis.
3. Re-evaluate a representative fixed detector pool, reporting standalone benchmark performance, standalone predictive utility, and beyond-basis predictive contribution with source-level uncertainty.

### 11.2 What can be claimed if primary controls and results support it

- Similar standalone benchmark performance can correspond to different estimated beyond-basis contributions.
- Some detector scores contain held-out label-predictive information not captured by the declared statistical basis and probe.
- Conditional contribution is protocol-relative and should be reported with source-level uncertainty.

### 11.3 What must not be claimed

- CDU identifies the intrinsically best detector.
- CDU is a replacement for VUS or other operational anomaly metrics.
- A positive CDU proves that a specific neural architecture causally learned semantic anomaly concepts.
- A negative finite-sample CDU proves negative mutual information.
- A detector with high CDU necessarily has better deployment value without an application-specific evaluation.

### 11.4 Contingency interpretations

| Outcome | Correct interpretation |
|---|---|
| rank separation persists with controls passing and robust CIs | evidence for beyond-basis rank divergence |
| ranks persist but source CIs are wide | exploratory estimated differences; avoid strong significance claims |
| results strongly depend on basis/probe | CDU is demonstrably protocol-relative; report this rather than hide it |
| source grouping removes Stage-2 separation | series-level evaluation likely benefited from source-specific transfer; report as benchmark/domain-transfer audit |

## 12. Explicitly paused or prohibited work

Until Protocol v1 primary results are frozen:

- do not add detector 10 or replace any of the nine frozen detectors;
- do not rerun detector training/scoring to obtain more favorable outputs;
- do not delete failed, collapsed, or weak series;
- do not change the 31 basis based on detector outcomes;
- do not alter source groups, folds, hyperparameter grid, loss, weights, rank mapping, or bootstrap after observing source-grouped outcomes;
- do not restart Stage 3 ensemble selection;
- do not start CDU-guided training;
- do not treat the old Stage-2 leaderboard as the final paper table;
- do not use global Hard subsets as the primary paper evidence without addressing family confounding;
- do not silently mix historical leaderboard VUS with pinned-cache or Protocol v1 results.

## 13. Important reports and artifacts

| Purpose | Primary files |
|---|---|
| Protocol contract | `protocol_v1.md`, `source_groups.json`, `protocol_v1_input_manifest.json` |
| Current controls | `protocol_v1_results/controls/`, `FOLD_AUDIT.csv`, `RUN_SIGNATURE.json` |
| Stage-2 authoritative audit | `STAGE2_FULL_AUDIT_REPORT.md`, `layer2_results/STAGE2_AUDITED_LEADERBOARD.csv` |
| Stage-2 field naming correction | `STAGE2_FIELD_DEFINITION_AUDIT.md`, `TIMESNET_CDU_CONSISTENCY_AUDIT.md` |
| Detector provenance | `layer2_results/STAGE2_DETECTOR_PROVENANCE.csv`, `DETECTOR_ENVIRONMENT_LOCK.md` |
| POLY provenance | `POLY_HISTORICAL_COMPAT.md`, `R0_REPRODUCIBLE_POLY.md`, `POLY_RAW_VUS_DISCREPANCY_AUDIT.md` |
| SubPCA audit | `SUBPCA_PINNED_AUDIT.md` |
| AnomalyTransformer audit | `ANOMALYTRANSFORMER_WRAPPER_AUDIT.md` |
| Hard-data preparation | `TRIVIAL_HARD_DATA_AUDIT.md`, `TRIVIAL_HARD_DATA_REPORT.md`, `data/trivial_difficulty_*.csv` |
| Historical Stage-3 attempt | `stage3_results/` (paused; not part of current claim) |

## 14. Short operational checklist

Before any Protocol v1 detector result is interpreted:

- [ ] all formal controls complete;
- [ ] formal control GO gate passes;
- [ ] clean/resume regression passes;
- [ ] pilot invariants pass;
- [ ] main-run manifest is frozen and hashed;
- [ ] detector result includes all four held-out losses;
- [ ] source-level contributions and selected hyperparameters are stored;
- [ ] no stale Stage-2/historical number was copied into Protocol v1 output;
- [ ] primary table and figures are regenerated from manifest-verified files.

## 15. Current bottom line

The project has already completed the expensive detector layer: nine frozen, audited point-wise detector score caches across 350 TSB-AD-U series. Stage 2 provides a valid pinned-cache historical/engineering result set, but the paper's main result is intentionally not yet claimed.

The active task is to qualify Protocol v1 as a stricter **measurement protocol**. Shared `L0/LB` baseline computation has finished for all 23 sources; formal controls are resumably running. Once the controls and pilot pass, the entire nine-detector main experiment becomes an offline evaluation over already cached scores, not a new detector-training campaign.
