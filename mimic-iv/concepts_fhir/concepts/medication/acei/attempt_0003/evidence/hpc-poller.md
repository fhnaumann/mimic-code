Evidence block — concept `acei`, stage `hpc-poller`, attempt 0003.

Slurm job `29599602` completed normally and produced a fresh full comparison;
the run did not crash or time out. Embedded Pathling/Spark execution passed the
schema hard gate: the five expected columns and compatible types matched.

Full-data result: `review`, exit code 2, tier `contested` with
`classification: unavailable_no_key`. The oracle has 112,014 rows and the
candidate 111,828 (row count is reported, not gated). Because acei has no
unique key, the multiset comparison reports 9,234 only-oracle rows and 9,048
only-candidate rows, and cannot distinguish missing rows from NULL-related
tuple changes. No `mismatch` or declared-unrepresentable blocker was reported.

Fetched artifacts:

- `comparison.full.json`
- `run_meta.full.json`

The candidate full Parquet remains on scratch at the remote attempt path. The
contested review must go through mismatch diagnosis before any equivalence
judge; no judge verdict is implied by this evidence.
