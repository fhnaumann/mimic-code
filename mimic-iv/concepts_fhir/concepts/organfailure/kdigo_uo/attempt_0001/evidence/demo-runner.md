# Demo Runner — kdigo_uo (attempt_0001)

Command: `uv run mimic_utils run-demo kdigo_uo` (embedded Pathling on Spark, no HTTP server)
Warehouse: `/Users/nau025/warehouses/mimic-iv-demo/delta`
Views registered: `urine_output`, `weight_durations`, `icu_encounter`

## Result

- Executed: **true** (shape.demo.json `executed`)
- Verdict: **shape_ok** (MAY PROCEED TO FULL DATA)
- Result row count: **7,317** (observation — **not gated**, non-gating)

## Shape comparison vs oracle_manifest (12 expected columns)

All 12 manifest columns present, matching:
| Column | Candidate type | Manifest type | Compatible |
|---|---|---|---|
| stay_id | int | INTEGER | yes |
| charttime | timestamp_ntz | TIMESTAMP | yes |
| weight | decimal(38,3) | DECIMAL(38,3) | yes |
| urineoutput_6hr | double | DOUBLE | yes |
| urineoutput_12hr | double | DOUBLE | yes |
| urineoutput_24hr | double | DOUBLE | yes |
| uo_rt_6hr | decimal(38,4) | DECIMAL(38,4) | yes |
| uo_rt_12hr | decimal(38,4) | DECIMAL(38,4) | yes |
| uo_rt_24hr | decimal(38,4) | DECIMAL(38,4) | yes |
| uo_tm_6hr | decimal(38,6) | DECIMAL(38,6) | yes |
| uo_tm_12hr | decimal(38,6) | DECIMAL(38,6) | yes |
| uo_tm_24hr | decimal(38,6) | DECIMAL(38,6) | yes |

- `incompatible_types`: [] (none)
- `missing_columns`: [] (none)
- Candidate carries 2 extra columns `icu_encounter_key` (string) and `patient_key`
  (string). These are NOT shape failures — the comparator records them as the
  manifest's `key_columns` (required_key_columns) used for the full-data
  `keyed_join` comparison, so the shape gate still reports `match: true` /
  `shape_ok`.

## Artifacts

- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0001/candidate.demo.parquet`
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0001/shape.demo.json`

Not evidence of correctness; grants permission to spend an HPC run.