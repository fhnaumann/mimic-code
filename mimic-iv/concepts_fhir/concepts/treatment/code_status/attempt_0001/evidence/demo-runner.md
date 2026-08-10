# Demo runner evidence — code_status attempt 0001

Command: `uv run mimic_utils run-demo code_status`.

The embedded Pathling/Spark demo execution completed successfully. Four
ViewDefinitions were registered (`cs_chart`, `cs_hosp`, `cs_icu`, and
`cs_patient`), the SQL executed, and Parquet was materialized.

Shape verdict: `shape_ok`. Candidate columns exactly match the manifest:
`subject_id`, `hadm_id`, `stay_id`, `charttime`, `fullcode`, `cmo`, `dni`, and
`dnr`. Types are compatible exactly: seven `INTEGER` columns and one
`TIMESTAMP` column. Demo row count was 147; it is observation only and was not
used as a gate. The oracle full-data row count is 269,072.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0001/shape.demo.json`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0001/candidate.demo.parquet/`
