# Demo-runner evidence

`uv run mimic_utils run-demo kdigo_creatinine` completed successfully for attempt 0002 using embedded Pathling on Spark. Three ViewDefinitions registered and executed without errors.

The shape verdict is `shape_ok`. The six oracle columns (`hadm_id`, `stay_id`, `charttime`, `creat`, `creat_low_past_48hr`, `creat_low_past_7day`) matched by name and compatible type; `incompatible_types` was empty. The required opaque key outputs (`patient_key`, `encounter_key`, `icu_encounter_key`) were reported as informational `extra_columns`, not unexpected columns, and were present as strings. Demo row count was 1,272 and was not gated.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_creatinine/attempt_0002/candidate.demo.parquet/`
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_creatinine/attempt_0002/shape.demo.json`
