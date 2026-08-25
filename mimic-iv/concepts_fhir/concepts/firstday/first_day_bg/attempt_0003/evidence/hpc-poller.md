# HPC-poller evidence

Slurm job `30486097` completed successfully after two polls. The full comparator returned `match` for replayed attempt_0003: keyed comparison on `stay_id`, 73,181 candidate rows versus 73,181 oracle rows, 73,181 identical, and zero `only_oracle`, `only_candidate`, `differing_conflict`, or `differing_null_only` rows. Schema matched with no missing or incompatible columns; `patient_key` and `icu_encounter_key` were the required candidate-side key columns. No judge or diagnostician was required.

Produced artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in this attempt directory. Slurm elapsed time was 285 seconds; execution was 279.57 seconds and comparison 1.751 seconds.
