## Evidence

Command: `uv run mimic_utils run-demo first_day_lab` using embedded Pathling on
Spark over the local demo Delta warehouse. Exit code was 0. All dependency,
Patient, and ICU Encounter ViewDefinitions registered; `concept.sql` executed
and wrote Parquet without errors.

The shape artifact reports `shape_ok`: actual and expected columns match with
no missing or unexpected columns, while `icu_encounter_key` and `patient_key`
are correctly recognized as manifest-required key columns. All types are
compatible, including the eight `abs_*` metric pairs as `DECIMAL(38,4)` and
the remaining metrics as `DOUBLE`; `subject_id` and `stay_id` are INTEGER.
The observed demo row count was 140, explicitly non-gating (full oracle count
reported as 73,181). This pass only authorizes the full-data run.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/firstday/first_day_lab/attempt_0001/candidate.demo.parquet`
- `mimic-iv/concepts_fhir/concepts/firstday/first_day_lab/attempt_0001/shape.demo.json`
