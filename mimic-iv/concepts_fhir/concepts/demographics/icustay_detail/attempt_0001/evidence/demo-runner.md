## Evidence

Concept: `icustay_detail`, attempt 0001. Controller was in

`uv run mimic_utils run-demo icustay_detail` executed cleanly using embedded
Pathling on Spark over the local demo Delta warehouse and wrote Parquet. All
three ViewDefinitions registered and `concept.sql` ran without errors.

Shape verdict: `shape_ok` / pass. The returned 18 column names exactly match
the oracle columns, with no missing or extra columns. Types were compatible:
INTEGER identifiers, VARCHAR strings, DATE death date, TIMESTAMP_NTZ
stay flags, and DECIMAL(38,2) ICU LOS.

The demo returned 140 rows versus 73,181 full oracle rows. Row count was
reported only and was not gated, as required; the port may proceed to full
data.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/demographics/icustay_detail/attempt_0001/candidate.demo.parquet/`
- `mimic-iv/concepts_fhir/concepts/demographics/icustay_detail/attempt_0001/shape.demo.json`

No implementation artifacts, notes, carryover, or git state were modified.
