# HPC poller evidence — vasopressin attempt_0003

- Ran: `uv run mimic_utils hpc-poll vasopressin` for Slurm job `30485928`.
- Result: job completed successfully; comparator verdict `review`, tier `gap_shaped`.
- Checked: schema matched; oracle and candidate each had 25,892 rows; there were 0 `only_oracle`, 0 `only_candidate`, 0 conflicts, and 25,892 `differing_null_only` rows solely on declared `linkorderid`. All 25,892 representable rows were identical.
- Routing: `judge_required=true`, `diagnostician_required=false`; no diagnostician was spawned.
- Produced: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in this attempt directory. Slurm elapsed time was 24 seconds.
