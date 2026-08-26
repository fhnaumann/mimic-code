## HPC poller evidence

Concept `sofa`, attempt `0001`, Slurm job `30534326`. The job completed and
the comparator artifact was fetched; `hpc_accounting.json` records
`ElapsedRaw = 2277` seconds. This was a real result, not a queue exit or crash.

Full-data schema identity held across 31 columns, with equal row counts of
6,043,902. The candidate reproduced 6,041,964 rows identically (99.97%) and
had 1,938 `differing_conflict` rows. Conflicts were concentrated in
`cardiovascular_24hours` (1,598), `sofa_24hours` (1,598), `cardiovascular`
(535), and `rate_norepinephrine` (1).

The comparator verdict is `review`, tier `contested`, with both
`diagnostician_required: true` and `judge_required: true`. DST conflict
attribution was attempted but attributed 0/1,938 rows, so it is incomplete
and cannot explain the divergence. The judge bar requires a cited upstream
`mimic-fhir` ETL statement and proof that the oracle value is unrecoverable;
the contested result must therefore go to diagnosis before the judge.

Artifacts fetched: `comparison.full.json`, `run_meta.full.json`, and
`hpc_accounting.json` under
`mimic-iv/concepts_fhir/concepts/score/sofa/attempt_0001/`. No state transition
or implementation edit was made.
