# HPC-poller evidence

Job `29714574` completed normally (`sacct` state `COMPLETED`, 25 seconds;
two polls), and the poller fetched `comparison.full.json`, `run_meta.full.json`,
and `hpc_accounting.json` into attempt_0001. The full comparator returned
`mismatch`, not `review`, with schema identity true and equal row counts
(candidate 24,470; oracle 24,470; row count is evidence only).

The machine-provable contradiction is one
`false_unrepresentable_declaration`: `linkorderid` is part of the manifest
natural key and therefore cannot be declared unrepresentable. Because the
candidate emits NULL for that key, the keyed diff aligns no rows: 24,470
`only_candidate` and 48,940 `only_oracle`, with zero identical rows and no
value conflicts/null-only differences. The judge was not called, as required
for `mismatch`. Artifacts: `comparison.full.json`, `run_meta.full.json`,
`hpc_accounting.json`, and existing `hpc_job.json` in the attempt directory.
