# Demo runner evidence — acei attempt 0006

- Command: `uv run mimic_utils run-demo acei`.
- Embedded Pathling 9.6.0 on Spark executed the five ViewDefinitions and
  `concept.sql` successfully.
- Shape verdict: `shape_ok`; all oracle columns were present, required
  `patient_key` and `encounter_key` columns were present, and there were no
  incompatible types or unexpected columns after manifest key handling.
- Observed demo row count: 107. This was reported only and was not gated.
- The demo produced no errors and did not transition controller state.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/medication/acei/attempt_0006/shape.demo.json`
- `mimic-iv/concepts_fhir/concepts/medication/acei/attempt_0006/candidate.demo.parquet/`
