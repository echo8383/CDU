# R0 detector parity screening

## Decision

This screening is R0-only. No CDU was run. A detector is eligible for
Layer-2 CDU only if it has an official-compatible point-wise output and every
screened sequence satisfies:

```text
abs(VUS_reproduced - VUS_official) <= 1e-6
length_y == length_score
finite_ratio == 1
window parity == True
```

## Screen scope

The screening table covers all 32 detector columns in `uni_vuspr.csv`.
Existing official-compatible parity outputs were available for the three
existing R0 sequences:

```text
010_NAB_id_10_WebService_tr_500_1st_271.csv
039_WSD_id_11_WebService_tr_1746_1st_1846.csv
331_UCR_id_29_Facility_tr_50000_1st_837400.csv
```

No missing detector was silently treated as passing. Missing point-wise
outputs are explicit FAILs and must be screened before CDU.

## Results

| Detector | Screened sequences | Max abs VUS diff | Length | Finite | Window | Status |
|---|---:|---:|---|---:|---|---|
| POLY | 3 | 4.996e-16 | PASS | 1.0 | PASS | **PASS** |
| Sub-PCA | 3 | 8.499e-05 | PASS | 1.0 | PASS | **FAIL** |
| Other 30 detectors | 0 | n/a | n/a | n/a | n/a | **FAIL — no screened score output** |

The complete machine-readable table is `r0_detector_screening.csv`.

## Interpretation

`POLY` is the only detector currently eligible for Layer-2 CDU under strict
R0. `Sub-PCA` has correct length, finite scores, and compatibility windows,
but fails the VUS tolerance. All other detectors fail screening because no
official-compatible point-wise output/cache has yet been screened; this is a
conservative provenance failure, not a claim about their detector quality.

## Gate

**R0 overall: FAIL.** Do not run real detector CDU for Sub-PCA or any detector
except POLY until the detector has a completed strict parity screen. This report
does not authorize a full CDU run; it only identifies the current eligible
detector.
