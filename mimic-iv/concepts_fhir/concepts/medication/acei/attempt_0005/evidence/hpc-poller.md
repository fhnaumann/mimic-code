# HPC poller evidence — `acei`, attempt `0005`

Job `29719864` completed cleanly in 32 seconds with no fatal markers. The
full-data comparator returned `review`, not a polling failure. Schema identity
matched and candidate/oracle row counts were both 112,014 (reported only).
There were 102,948 identical rows (91.91%), 9,059
`differing_null_only` values (starttime NULL on 9,058 and stoptime NULL on
9,051), and 7 `differing_conflict` values (starttime on 5 rows, stoptime on 3).
The unkeyed comparison classified the residual as `paired_residual`, with tier
`contested`, so diagnosis is required before convening the judge.

Artifacts:
- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`
