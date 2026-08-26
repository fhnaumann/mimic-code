# HPC poller evidence — `first_day_sofa`

## Result

- Job `30511592` completed normally; poll outcome `complete`.
- Comparison verdict: `review`, tier `contested`; `judge_required: true`, `diagnostician_required: true`.
- Oracle and candidate row counts were both 73,181; row count was not used as a gate.
- 73,159 rows were identical (99.97%); 22 `differing_conflict` rows remained, on `cardiovascular` and `sofa` (0.030% of oracle rows).
- No gap-shaped divergence and no declared unrepresentable columns were reported.
- DST attribution was not attempted because this concept has no datetime output column.
- A contested result requires diagnosis and an upstream ETL citation before judge review.

## Evidence block

Read/checks: polled only job `30511592` from `hpc_job.json` using the sanctioned CLI, distinguished normal completion from the comparison verdict, and read the fetched comparison and runtime/accounting artifacts. Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in this attempt. Slurm elapsed time was 2,205 seconds; no implementation artifacts or sibling jobs were changed and no commit was made.
