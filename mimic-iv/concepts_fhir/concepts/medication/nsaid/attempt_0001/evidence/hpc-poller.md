# Evidence — hpc-poller

Concept `nsaid`, attempt `0001`.

`uv run mimic_utils hpc-poll nsaid` completed normally after two polls; Slurm
job `29910678` completed in 29 seconds. The full comparator returned `review`,
not a crash: schema matched, row count was 235,678 on both sides, and the
unkeyed residual paired 1:1. It reported 225,384 identical rows, 10,276
`differing_null_only` rows, and 18 attributed conflicts (12 `starttime`, 6
`stoptime`) fully replayed to the upstream New York `TIMESTAMPTZ` DST cast.

Artifacts: `comparison.full.json`, `run_meta.full.json`, and
`hpc_accounting.json` in this attempt directory.
