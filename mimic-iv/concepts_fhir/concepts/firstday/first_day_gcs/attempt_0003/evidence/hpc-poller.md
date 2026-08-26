# HPC poller evidence — `first_day_gcs`, attempt 0003

The poller followed job `30532631` to Slurm `COMPLETED`, fetched a fresh
`comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`, and
reported a comparator verdict of `match`.

The keyed comparison used `stay_id` and reproduced all 73,181 of 73,181
oracle rows identically (100.00%). Candidate and oracle row counts were both
73,181; row count was reported but not used as a gate. There were zero
`only_oracle`, `only_candidate`, `differing_null_only`, or
`differing_conflict` rows, with no schema incompatibilities or missing
columns. The required key companions were present. No judge or diagnostician
was invoked because the comparator returned `match`.

Full execution took 223.582 seconds, comparison 1.178 seconds, and Slurm
accounting recorded 227 elapsed seconds. Artifacts:

- `mimic-iv/concepts_fhir/concepts/firstday/first_day_gcs/attempt_0003/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/firstday/first_day_gcs/attempt_0003/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/firstday/first_day_gcs/attempt_0003/hpc_accounting.json`
