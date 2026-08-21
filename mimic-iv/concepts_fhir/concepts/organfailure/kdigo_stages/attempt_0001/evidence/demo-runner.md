## Evidence block

**Concept:** kdigo_stages
**Attempt:** attempt_0001
**Verdict:** shape_ok

**Executed:** Yes — `uv run mimic_utils run-demo kdigo_stages` completed with exit code 0 (Spark lease acquired in 0s, embedded Pathling on Spark over the demo Delta warehouse at `/Users/nau025/warehouses/mimic-iv-demo/delta`). No prior timed-out artifacts needed cleanup; artifacts were written fresh by this run. No write-once artifacts were edited or replaced.

**Column-name comparison — matching, with declared-key extras only:**
All 15 oracle columns present, none missing, none unexpected:
`subject_id, hadm_id, stay_id, charttime, creat_low_past_7day, creat_low_past_48hr, creat, aki_stage_creat, uo_rt_6hr, uo_rt_12hr, uo_rt_24hr, aki_stage_uo, aki_stage_crrt, aki_stage, aki_stage_smoothed`.
The 3 candidate extra columns — `patient_key`, `encounter_key`, `icu_encounter_key` — correspond exactly to the manifest's declared `key_columns` (`["encounter_key","icu_encounter_key","patient_key"]`) and are the only extras. `shape.demo.json` lists them under `extra_columns` separately from `unexpected_columns` (which is empty), and the gate reports `match: true`.

**Type comparison — compatible (no incompatible types):**
- `subject_id` int / `INTEGER` ✓
- `hadm_id` int / `INTEGER` ✓
- `stay_id` int / `INTEGER` ✓
- `charttime` `timestamp_ntz` / `TIMESTAMP` ✓
- `creat_low_past_7day`, `creat_low_past_48hr`, `creat` double / `DOUBLE` ✓
- `aki_stage_creat`, `aki_stage_uo`, `aki_stage_crrt`, `aki_stage`, `aki_stage_smoothed` int / `INTEGER` ✓
- `uo_rt_6hr`, `uo_rt_12hr`, `uo_rt_24hr` decimal(38,4) / `DECIMAL(38,4)` ✓
- `shape.demo.json` `incompatible_types: []`.

**Row count — non-gating observation:** candidate returned **8,729** rows on the demo cohort (oracle full reference count 4,011,255; demo is a subset of this non-keyed concept, so a row-count difference is expected and not gated).

**Exact artifacts produced:**
- `/Users/nau025/Documents/mimic-code/mimic-iv/concepts_fhir/concepts/organfailure/kdigo_stages/attempt_0001/candidate.demo.parquet/`
- `/Users/nau025/Documents/mimic-code/mimic-iv/concepts_fhir/concepts/organfailure/kdigo_stages/attempt_0001/shape.demo.json`

No errors captured — the gate logged `Shape gate: SHAPE OK` and `Overall: MAY PROCEED TO FULL DATA`.
