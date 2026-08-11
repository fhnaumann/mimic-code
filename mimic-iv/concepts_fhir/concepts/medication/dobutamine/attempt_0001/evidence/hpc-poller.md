# HPC-poller evidence

Polled job `29710383` with `uv run mimic_utils hpc-poll dobutamine`. Outcome was `complete` with a fetched genuine comparator result (Slurm COMPLETED; elapsed 25 seconds). Full oracle and candidate each had 8,513 rows; row count was not gated. Schema matched exactly for the six columns and types. Comparator verdict was `review`, tier `contested`.

Keyed diff on `(stay_id,starttime)`: `only_candidate` 2, `only_oracle` 2, `differing_conflict` 1 on `endtime`, and `differing_null_only` 8,510 on declared-and-confirmed unrepresentable `linkorderid`; identical rows 0 overall and 8,510/8,513 on representable columns. The one endtime conflict was a +1 hour candidate shift. Full artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in attempt 0001.
