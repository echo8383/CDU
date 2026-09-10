# Three-detector smoke report

Smoke protocol: the three fixed series `001_NAB...`, `141_MSL...`, and
`179_SMD...`; seed 2024; each call repeated twice; score length and finite
checks performed. The CSVs contain the exact hashes and runtime.

| detector | execution type | smoke | observed two-run wall time | estimated one-run 350-series time* |
|---|---|---:|---:|---:|
| TranAD | train-then-score | PASS (3/3) | 17.13s, 3.00s, 24.17s | ~43 min |
| FITS | train-then-score | PASS (3/3) | 5.58s, 2.98s, 26.61s | ~34 min |
| M2N2 | train-then-score + online test-time adaptation | PASS (3/3) | 4.46s, 2.54s, 2.81s | ~10 min |

\*Estimate uses roughly half the two-run smoke wall time per series, multiplied
by 350; sequence length and GPU contention make this indicative only. No
350-series sweep was run in this task.

All smoke rows have exact score/label lengths, finite ratio 1.0, and identical
seed-2024 score hashes between repetitions. M2N2 starts a fresh model per call,
so online adaptation state is not shared across series.
