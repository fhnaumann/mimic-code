# HPC poller evidence — `first_day_sofa` attempt 0002

## Result

- Job `30512546` completed normally; poll outcome `complete`.
- Comparison verdict: `review`, tier `contested`; `judge_required: true`, `diagnostician_required: true`.
- Schema matched and candidate/oracle row counts were both 73,181; row count was not gated.
- 73,157 rows were identical (99.97%); 24 `differing_conflict` rows remained, all on `cardiovascular` and `sofa` (0.033%). Candidate cardiovascular/sofa values were one point below the oracle in the sampled conflicts.
- `only_oracle`, `only_candidate`, and `differing_null_only` were all zero. DST attribution was not attempted because the target has no datetime output column.

## Evidence block

Read/checks: polled only job `30512546` from its attempt-local `hpc_job.json`, distinguished normal Slurm completion from the comparator review, and read the fetched comparison/runtime/accounting artifacts. Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in attempt 0002. Slurm elapsed time was 2,053 seconds. No implementation artifacts, sibling jobs, or commits were touched.
