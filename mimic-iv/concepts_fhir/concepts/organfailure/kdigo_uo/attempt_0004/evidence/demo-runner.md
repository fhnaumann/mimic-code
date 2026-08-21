# Demo shape-gate evidence — kdigo_uo attempt 0004

The run executed cleanly via `uv run mimic_utils run-demo kdigo_uo` using embedded Pathling on Spark over the local demo Delta warehouse. Views registered: `urine_output`, `weight_durations`, and `icu_encounter`; no execution error.

All 12 oracle columns are present and named correctly: `stay_id`, `charttime`, `weight`, `urineoutput_6hr`, `urineoutput_12hr`, `urineoutput_24hr`, `uo_rt_6hr`, `uo_rt_12hr`, `uo_rt_24hr`, `uo_tm_6hr`, `uo_tm_12hr`, and `uo_tm_24hr`. `icu_encounter_key` and `patient_key` are present as the manifest-declared candidate key columns and are not unexpected. No columns are missing.

Types are compatible: integer, timestamp_ntz, decimal(38,3), double, decimal(38,4), and decimal(38,6) match the manifest expectations; `incompatible_types` is empty. The demo candidate returned 7,317 rows; row count is informational and was not gated.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0004/candidate.demo.parquet`
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0004/shape.demo.json` (`shape_ok`, `executed: true`)
