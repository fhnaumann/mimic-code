# HPC-poller evidence — blood_differential attempt 0003

Slurm job `30103841` completed successfully in 118 seconds. The fetched
full-data comparator result is `review`, not a crash or mismatch. The schema
matches: all 20 manifest columns have compatible types and the three extra
columns (`patient_key`, `encounter_key`, `specimen_key`) are the manifest
required resource-key columns. Oracle and candidate row counts are both
3,171,906; counts are reported only and are not a gate.

The keyed diff reproduced 3,171,706/3,171,906 rows identically. It contains
200 `differing_conflict` rows on `charttime`, with zero `only_oracle`,
`only_candidate`, or `differing_null_only` rows. The comparator replayed all
200 conflicts to `upstream_timestamptz_dst_shift` in `America/New_York`, with
zero residual rows, so the result is tier `attributed`,
`judge_required: true`, and `diagnostician_required: false`. The artifact
requires the judge to confirm that the cited upstream ETL writes the FHIR
element feeding `charttime` and that the 200-row fraction is consistent with
DST-gap rarity.

Artifacts fetched:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`

The candidate full Parquet remains on the remote scratch path. No job was
resubmitted or cancelled, and no implementation artifact was modified.
