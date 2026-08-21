# HPC-poller evidence — `urine_output_rate`, attempt 0002

Slurm job `30313105` completed and produced/fetched the full comparison. The
poll outcome was `complete`; runtime was 230 seconds. The comparator verdict
is `review`, tier `contested`, with `judge_required: true` and
`diagnostician_required: true`.

The candidate has 3,321,511 rows versus 3,321,747 oracle rows (row count is
not gated), with 3,319,937 identical rows (99.95%). There are 1,417
`differing_conflict` rows, 393 `only_oracle`, and 157 `only_candidate`; all
unpaired rows are fully attributed to the upstream New York DST cast, while
1,185 conflicts remain unexplained and must be diagnosed before convening the
judge. No `differing_null_only` rows were reported.

Fetched artifacts: `comparison.full.json`, `run_meta.full.json`, and
`hpc_accounting.json` in attempt 0002. No artifacts were edited and no commit
was made.
