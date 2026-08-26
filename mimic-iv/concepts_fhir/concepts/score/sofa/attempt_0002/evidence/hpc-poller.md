## HPC poller evidence

Concept `sofa`, attempt `0002`, Slurm job `30536435`. The job completed cleanly
(`ElapsedRaw` approximately 1,809 seconds) and fetched a valid comparator
artifact. Full execution was embedded Pathling on Spark.

Schema identity held, including the required key columns; candidate and oracle
both contained 6,043,902 rows. The candidate reproduced 6,042,764 rows
identically (99.98%). The only diff class was 1,138 `differing_conflict` rows:
`cardiovascular_24hours` 1,022, `sofa_24hours` 1,022,
`cardiovascular` 294, and `rate_norepinephrine` 1. There were no
`only_candidate`, `only_oracle`, `differing_null_only`, or declared gaps.

The comparator verdict is `review`, tier `contested`, with both
`diagnostician_required: true` and `judge_required: true`. DST attribution was
attempted but attributed 0/1,138 rows, leaving the full residual contested.
The result must go to the diagnostician before the equivalence judge.

Fetched artifacts: `comparison.full.json`, `run_meta.full.json`, and
`hpc_accounting.json` under
`mimic-iv/concepts_fhir/concepts/score/sofa/attempt_0002/`. No state transition
or implementation edit was performed.
