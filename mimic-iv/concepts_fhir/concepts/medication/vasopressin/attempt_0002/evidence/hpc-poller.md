# HPC poll evidence — vasopressin attempt 0002

The full-data job completed successfully and the poller fetched a fresh
`comparison.full.json`; this was a comparator verdict, not a crash or timeout.
The schema matched and both oracle and candidate had 25,892 rows. The keyed
comparison used `(stay_id, starttime)`.

Comparator verdict: `review`, tier `gap_shaped`, with
`judge_required: true` and `diagnostician_required: false`. The declared
typed-NULL `linkorderid` gap was confirmed: 25,891 `differing_null_only` rows
and `identical_representable` 25,891/25,892. There was one additional
`differing_conflict` on `endtime`, candidate `2118-03-13 03:55` versus oracle
`02:55`; the comparator exhaustively attributed it to the upstream
`TIMESTAMPTZ` DST-gap cast with zero residual. There were no only-oracle or
only-candidate rows. The judge is still required; the diagnostician is
skipped because attribution is complete.

Artifacts fetched: `comparison.full.json`, `run_meta.full.json`, and
`hpc_accounting.json` in this attempt. Slurm elapsed time was 24 seconds. No
implementation artifacts were changed and no semantic decision was made.
