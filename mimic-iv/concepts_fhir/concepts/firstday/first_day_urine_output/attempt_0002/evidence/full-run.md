# Full-data convergence evidence

- Concept: `first_day_urine_output`; attempt `0002` replayed the byte-identical port from attempt `0001` after the warehouse rebuild.
- Slurm job: `30486420`; outcome `complete`; accounting state `COMPLETED`; elapsed 84 seconds.
- Comparator verdict: `match`.
- Schema: matched; expected value columns were present with compatible types and required `patient_key`/`icu_encounter_key` columns were present.
- Keyed comparison key: `stay_id`.
- Full counts: candidate 73,181; oracle 73,181; row-count delta 0 (reported, not gated).
- Fidelity: 73,181 identical rows (100.00%); zero `only_oracle`, `only_candidate`, `differing_null_only`, and `differing_conflict` rows; divergence tier `none`.
- No diagnostician or equivalence judge was required because the deterministic comparator returned `match`.
- Artifacts: `comparison.full.json`, `run_meta.full.json`, `hpc_accounting.json`.
