Concept: icustay_times (attempt_0004)

Job id: 30484697 (per hpc_job.json; matched the polled id). Poll outcome: `complete` — job exited the queue with a fetched comparison after 2 polls; not a crash or timeout.

Comparator verdict: `match` (exit 0). Divergence tier `none`; `diagnostician_required=false`; `judge_required=false`; classification `keyed`.

Slurm elapsed runtime: 85 seconds (`hpc_accounting.json`, state COMPLETED, source `slurm_sacct`).

Row counts: candidate 73,181 / oracle 73,181; identical 73,181 (100.00%); differing 0, only_oracle 0, only_candidate 0, differing_null_only 0, differing_conflict 0.

Schema: required columns match exactly (`subject_id`, `hadm_id`, `stay_id`, `intime_hr`, `outtime_hr`); extra identity keys `patient_key`, `encounter_key`, `icu_encounter_key` are expected; no missing/incompatible types.

Artifacts fetched: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` under attempt_0004/. No immutable artifacts were edited and no commit was made.
