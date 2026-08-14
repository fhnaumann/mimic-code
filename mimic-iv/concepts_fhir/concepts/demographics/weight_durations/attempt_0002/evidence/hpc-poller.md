# HPC-poller evidence

The sanctioned poll completed job `29956802` and fetched a valid full comparison, not a crash. Schema identity passed and candidate/oracle row counts were both 272,445 (reported, not gated). The verdict is `review`, tier `contested`, with `judge_required: true` and `diagnostician_required: true`.

The corrected attempt removed the two `weight_type` tie-order conflicts. The remaining diff is 272,357 identical rows (99.967%), 56 `differing_conflict` rows (all 56 on `starttime`, with one also differing on `weight`), 38 attributed `only_oracle`, and 32 attributed `only_candidate`; there are no gap-shaped or unresolvable classes. The endtime key attribution is complete (38/32 paired, including six collisions), while 39 of 56 value conflicts replay the upstream DST cast and 17 remain to be diagnosed. Slurm elapsed time was 79 seconds.

Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` under attempt 0002.
