**Concept:** `first_day_height`
**Attempt:** `attempt_0002`
**Job:** Slurm `30486234`

Poll outcome was `complete`; the job completed without fatal markers and fetched the full-data artifacts. The deterministic comparator verdict was `match` (exit 0).

- Candidate rows: 73,181; oracle rows: 73,181; delta 0 (reported, not a gate)
- Identical: 73,181/73,181 (100.00%), `identical_fraction: 1.0`
- Diff classes: `only_oracle` 0, `only_candidate` 0, `differing_conflict` 0, `differing_null_only` 0, `differing` 0
- Divergence tier: `none`; `judge_required: false`; `diagnostician_required: false`
- Schema matched. Candidate types were `subject_id int`, `stay_id int`, `height decimal(38,2)`, with required FHIR key columns `patient_key string` and `icu_encounter_key string`; no missing or incompatible columns.
- Natural key: `stay_id`
- Slurm elapsed: 122 seconds (`hpc_accounting.json`, `slurm_sacct`); run metadata: execute 119.694s, compare 1.018s.

Artifacts fetched into this attempt: `comparison.full.json`, `run_meta.full.json`, `hpc_accounting.json`.
