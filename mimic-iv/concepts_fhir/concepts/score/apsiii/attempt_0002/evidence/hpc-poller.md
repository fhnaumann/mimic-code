# HPC-poller evidence

Concept: `apsiii`, attempt `0002`.

Job `30536393` completed with Slurm state `COMPLETED`; the fetched full-data
comparison outcome is `complete` and the deterministic comparator verdict is
`match` (exit 0). Slurm elapsed time was 1917 seconds.

Candidate and oracle each contain 73,181 rows. The keyed comparison on
`stay_id` reports 73,181 identical rows (100.00%) and zero
`only_oracle`, `only_candidate`, `differing_null_only`, or
`differing_conflict` rows. Schema matched with all 21 expected columns and the
three declared FHIR key columns; no incompatible types or missing columns.
There is no divergence tier, and neither judge nor diagnostician is required.
Row count is reported evidence, not the gate.

Fetched artifacts:
- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`

No dataset-wide quirk was reported or appended by this stage.
