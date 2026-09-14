# Protocol Fast outputs

Generated outputs are ignored by Git. Expected layout:

```text
shared_baseline/
  by_source/<Source>.csv|json
  PER_SERIES.csv
main/<Detector>/
  by_source/<Source>.csv|json
  PER_SERIES.csv
  PER_SOURCE.csv
  SUMMARY.csv
logs/
```

