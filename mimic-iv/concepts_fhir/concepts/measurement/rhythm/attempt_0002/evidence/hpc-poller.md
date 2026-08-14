# HPC-poller evidence — rhythm attempt 0002

Job `29946229` completed cleanly after two polls. The full comparator returned
`review`, tier `attributed`, with schema identity and no execution failure.
Oracle rows were 5,873,723 and candidate rows 5,873,120; 5,872,983 rows were
identical (99.9874%). It classified 95 differing conflicts, 645 oracle-only
rows, and 42 candidate-only rows, all fully attributed to the upstream
America/New_York DST TIMESTAMPTZ shift, with zero residuals. The corrected
citations now include `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`.
The judge is required; the diagnostician is not. Artifacts are
`comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in
attempt_0002.
