# HPC poller evidence — weight_durations attempt 0004

The blocking poll of Slurm job `30485990` completed successfully. The full
comparator returned `match`: all 272,445 oracle rows were reproduced by
272,445 candidate rows, with zero row delta and `identical_fraction = 1.0`.
The schema matched, including the required `icu_encounter_key` and
`patient_key` columns. All divergence classes were zero; tier was `none`, so
no diagnostician or equivalence judge was required.

Fetched artifacts: `comparison.full.json`, `run_meta.full.json`, and
`hpc_accounting.json` in this attempt. This consumed one full-data run.
