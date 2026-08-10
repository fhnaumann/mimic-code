# Evidence: demo-runner (`bg`, attempt_0006)

Outcome: `shape_ok` / pass. `uv run mimic_utils run-demo bg` executed embedded
Pathling 9.6.0 on Spark, materialized all five views, and ran `concept.sql`
without errors.

The candidate returned exactly the 27 manifest columns with no missing or extra
columns. Types were compatible, including `charttime TIMESTAMP_NTZ`, specimen
string, `fio2_chartevents FLOAT`, `aado2_calc DECIMAL(38,4)`, and the remaining
numeric DOUBLE columns. The demo produced 889 rows; this is informational only
and is not a gate.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0006/shape.demo.json`
- `mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0006/candidate.demo.parquet/`

The port is permitted to proceed to full-data validation. No implementation
artifacts or `MIMIC_NOTES.md` were modified.
