# HPC-poller evidence — `first_day_rrt`

Polled Slurm job `30306104` to normal completion and fetched the full-data
artifacts. The poll outcome was `complete`; the comparator verdict was
`match`, so no diagnostician or equivalence judge was required.

`comparison.full.json` reports a keyed join on `stay_id`, schema match, and
73,181 of 73,181 rows identical. `only_oracle`, `only_candidate`,
`differing_null_only`, and `differing_conflict` were all zero; the divergence
tier was `none`. Required key columns `icu_encounter_key` and `patient_key`
were present and no incompatible types or missing columns occurred.

Artifacts fetched/written include `comparison.full.json`, `run_meta.full.json`,
and `hpc_accounting.json`; candidate full Parquet remains on scratch. Slurm
accounting reports 186 elapsed seconds, with 182.859 seconds execution and
0.995 seconds comparison.
