# HPC-poller evidence

The poller read the write-once job record for attempt 0003 and polled job
`30079912` to normal completion. Slurm accounting reports 123 seconds. The
full embedded Pathling/Spark run executed successfully and produced a schema
match with 272,445 candidate rows and 272,445 oracle rows; row count was
reported, not gated.

The comparator verdict is `review`, tier `contested`, with
`judge_required: true` and `diagnostician_required: true`. It reports 272,357
identical rows (99.9677%), 56 `differing_conflict` rows (56 on `starttime`, one
also on `weight`), 38 `only_oracle` rows, and 32 `only_candidate` rows. The
`starttime` column is in the manifest key. All 38 oracle-only and all 32
candidate-only rows were fully key-attributed to the upstream DST replay; 39
of 56 conflicts replay directly or through key collision and 17 conflicts
remain for source-side diagnosis. The artifact cites the upstream timestamp
sites, including `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` and
`mimic-fhir/sql/fhir_encounter_icu.sql:31-32,97-100` as relevant to this
concept's evidence.

Fetched artifacts:

- `mimic-iv/concepts_fhir/concepts/demographics/weight_durations/attempt_0003/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/demographics/weight_durations/attempt_0003/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/demographics/weight_durations/attempt_0003/hpc_accounting.json`
