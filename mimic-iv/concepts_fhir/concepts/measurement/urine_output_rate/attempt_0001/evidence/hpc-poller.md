# HPC-poller evidence — `urine_output_rate`

Slurm job `30312029` completed and the CLI fetched a fresh comparison. The
poll outcome was `complete` (not crash/timeout); Slurm elapsed time was 234
seconds.

`comparison.full.json` reports a schema-valid `review` at tier `contested`,
with both `diagnostician_required: true` and `judge_required: true`. The
oracle has 3,321,747 rows and the candidate 3,321,511 (row count is not a
gate). The keyed diff reports 336,011 `differing_conflict` rows; 232 are
replayed to the known upstream DST transformation, leaving 335,779
unexplained contested conflicts. The attributed 393 `only_oracle` and 157
`only_candidate` rows re-pair completely, but the remaining conflict set must
be diagnosed before any judge review.

Fetched artifacts: `comparison.full.json`, `run_meta.full.json`, and
`hpc_accounting.json` in attempt 0001. No artifacts were edited and no commit
was made.
