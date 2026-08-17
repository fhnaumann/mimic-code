# Evidence: demo-runner

The embedded Pathling-on-Spark demo run for `age` attempt_0003 executed
successfully and returned `shape_ok`. The six manifest columns matched:
`subject_id`, `hadm_id`, `admittime`, `anchor_age`, `anchor_year`, and `age`.
The extra `patient_key` and `encounter_key` columns are the manifest-declared
required FHIR identity keys; there were no unexpected columns or missing keys.
Types were compatible: INTEGER/SMALLINT/BIGINT and timestamp_ntz versus the
manifest TIMESTAMP. The 275-row demo count is observation only and was not
gated.

Artifacts produced:

- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0003/candidate.demo.parquet`
- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0003/shape.demo.json`

The demo pass grants permission to spend a full-data run; it is not a
correctness or terminal verdict.
