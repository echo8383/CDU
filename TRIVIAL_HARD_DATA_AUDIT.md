# Trivial-Hard Data Audit

- Unique series: 350; 5-fold rows: 350; 10-fold rows: 350.
- 31 basis scorers, finite VUS: True.
- Leakage safety: each outer fold selects one scorer from training-series mean VUS only; no held-out series enters its own selection.
- No detector score, detector training, CDU output, or per-series best-of-31 oracle is imported or used.
- Point-wise cache alignment: PASS for all 350 series; event rows: 16308.

## Provenance

```json
{
  "dataset_files": 350,
  "dataset_sha256_manifest": "e020544584b2c1bacd7e62377b7e1d652d4ca391b3c4af54c55afec672942dd7",
  "basis_vus_source": "step2_oneliner_vuspr.csv",
  "basis_metric": "generate_curve(..., slidingWindow=100, opt, thre=250)[7]",
  "basis_pointwise_source": "layer2_results/basis_scores/*.npz rank-normalized basis curves",
  "basis_definitions": [
    "Var-8",
    "Var-16",
    "Var-32",
    "Var-64",
    "Var-96",
    "Var-128",
    "Var-256",
    "Range-8",
    "Range-16",
    "Range-32",
    "Range-64",
    "Range-96",
    "Range-128",
    "Range-256",
    "Last-1",
    "Last-2",
    "Last-3",
    "Last-8",
    "Last-16",
    "Last-32",
    "Last-64",
    "Centered-3",
    "Centered-16",
    "Centered-64",
    "AbsDiff-1",
    "AbsDiff-4",
    "AbsDiff-16",
    "MAD-32",
    "MAD-128",
    "SpecEnt-64",
    "SpecEnt-256"
  ],
  "window_logic": "fixed 100 from cached VUS artifact",
  "tsbad_commit": "8b363e350ae047a8115a594d1e9da64aae09b852",
  "fold_assignment": "deterministic np.array_split in uni_vuspr.csv order"
}
```