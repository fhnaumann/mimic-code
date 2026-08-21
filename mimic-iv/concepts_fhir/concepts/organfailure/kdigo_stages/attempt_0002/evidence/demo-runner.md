# Demo runner — kdigo_stages, attempt_0002

## Command

```
uv run mimic_utils run-demo kdigo_stages
```
from `/Users/nau025/Documents/mimic-code`, embedded Pathling-on-Spark over the demo Delta warehouse. State was already `VALIDATING_DEMO`.

## Result

- **Executed**: yes. Exit code 0. ViewDefinition preprocess of completed dependencies (crrt, kdigo_creatinine, urine_output, weight_durations, kdigo_uo) succeeded; 8 views registered.
- **Verdict**: `shape_ok` (`shape.demo.json` → `verdict: shape_ok`, `match: true`).
- **Row count**: 8,729 (observation only — NOT a demo gate).

## Schema comparison vs oracle manifest (`oracle_manifest.full.json`)

Oracle `kdigo_stages.columns` (15): `subject_id INTEGER`, `hadm_id INTEGER`, `stay_id INTEGER`, `charttime TIMESTAMP`, `creat_low_past_7day DOUBLE`, `creat_low_past_48hr DOUBLE`, `creat DOUBLE`, `aki_stage_creat INTEGER`, `uo_rt_6hr DECIMAL(38,4)`, `uo_rt_12hr DECIMAL(38,4)`, `uo_rt_24hr DECIMAL(38,4)`, `aki_stage_uo INTEGER`, `aki_stage_crrt INTEGER`, `aki_stage INTEGER`, `aki_stage_smoothed INTEGER`.

Candidate columns (18): the same 15, plus `patient_key string`, `encounter_key string`, `icu_encounter_key string`.

- **Column names**: matching — all 15 oracle columns present in candidate. `missing_columns: []`. `extra_columns: ['patient_key','encounter_key','icu_encounter_key']` — these are the manifest's declared `key_columns` (`encounter_key`, `icu_encounter_key`, `patient_key`), which the gate treats as required (`required_key_columns` all present, `missing_key_columns: []`). These are expected key additions for the full-data keyed diff, not a shape failure.
- **Column types**: compatible — `incompatible_types: []`. All 15 oracle types match candidate (`int`↔INTEGER, `timestamp_ntz`↔TIMESTAMP, `double`↔DOUBLE, `decimal(38,4)`↔DECIMAL(38,4)). No type failure even on gated/all-null columns.

## Gate verdict

`shape_ok` — executed, column names match, types compatible. Overall: **MAY PROCEED TO FULL DATA**. This is a shape gate only and is NOT evidence of correctness.

## Artifacts

- Candidate: `.../attempt_0002/candidate.demo.parquet`
- Shape gate: `.../attempt_0002/shape.demo.json`