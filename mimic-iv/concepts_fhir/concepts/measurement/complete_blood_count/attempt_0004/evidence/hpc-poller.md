# HPC poller evidence

Concept: `complete_blood_count`
Attempt: `attempt_0004`
Job: `30484162`

The Slurm job completed successfully. The full-data comparator returned an
exact `match` on the natural key `specimen_id`: 3,362,503 candidate rows and
3,362,503 oracle rows, with zero `only_oracle`, `only_candidate`,
`differing_conflict`, or `differing_null_only` rows. Schema identity also
passed, including the required FHIR resource-key columns. No judge or
diagnostician was required.

Artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`

Poll outcome was `complete`; Slurm elapsed time was 108 seconds.
