# HPC poller evidence — `gcs`

- Concept: `gcs`; attempt: `0002`; job: `29730161`.
- Read/checked: fetched `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` after Slurm completion.
- Result: job outcome `complete`; comparator verdict `review`; schema matched.
- Counts: oracle `1,637,763`, candidate `1,637,739` (row count reported, not gated); `1,637,665` identical rows.
- Divergence: tier `contested`; `74` `only_candidate`, `98` `only_oracle`, `0` `differing_conflict`, `0` `differing_null_only`; attribution empty. `diagnostician_required=true`, `judge_required=true`.
- Runtime: Slurm elapsed `155 s`; run metadata execute `151.575 s`, compare `1.328 s`.
- Artifacts: `comparison.full.json`, `run_meta.full.json`, `hpc_accounting.json`, and this evidence file. No diagnosis, state transition, or commit was made.
