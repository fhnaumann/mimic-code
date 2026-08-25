# Evidence — hpc-poller

Concept `gcs`, attempt `0008`; Slurm job `30503189`.

Poll outcome was `complete`; the deterministic full comparator verdict was `match`. The candidate reproduced 1,637,763/1,637,763 oracle rows identically (100.00%), with row-count delta 0. Keyed comparison used `[stay_id, charttime]`; all divergence classes were zero (`differing`, `differing_conflict`, `differing_null_only`, `only_candidate`, and `only_oracle`). Schema matched, with expected non-gating provenance key columns `patient_key` and `icu_encounter_key`; no judge or diagnostician was required. Slurm elapsed time was 197 seconds; run metadata reported 192.166 seconds execution and 1.571 seconds comparison.

Artifacts fetched: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in attempt `0008`. No artifacts were edited and no second job was launched.
