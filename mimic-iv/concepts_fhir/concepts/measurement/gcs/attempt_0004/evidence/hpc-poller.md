# HPC poller evidence

Concept `gcs`, attempt `0004`, Slurm job `29776217`.

The job completed successfully and the fetched full-data comparator verdict was
`match`. The keyed comparison on `(stay_id, charttime)` reproduced all
1,637,763 oracle rows identically: schema 8/8 matched, with zero
`only_oracle`, `only_candidate`, `differing_null_only`, or
`differing_conflict` rows. No judge or diagnostician was required. The row
counts were equal (reported, not gated). Slurm elapsed time was 198 seconds.

Artifacts: `comparison.full.json`, `run_meta.full.json`, and
`hpc_accounting.json` in the attempt directory.
