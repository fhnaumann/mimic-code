## Evidence

Corrected `icustay_detail` attempt 0002 passed the demo shape gate with
`uv run mimic_utils run-demo icustay_detail` using embedded Pathling 9.6.0 on
Spark over the demo Delta warehouse.

All three ViewDefinitions materialized and `concept.sql` executed cleanly.
All 18 oracle column names matched in order; missing and extra columns were
empty. Types were compatible, including INTEGER identifiers, VARCHAR strings,
DATE death date, TIMESTAMP_NTZ datetimes, BIGINT derivations, SMALLINT typed
NULL hospital expiry, DECIMAL(38,2) ICU LOS, and BOOLEAN first-stay flags.

The demo returned 140 rows versus 73,181 oracle rows. This row count was
reported only and not gated. Shape artifact verdict is `shape_ok`.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/demographics/icustay_detail/attempt_0002/candidate.demo.parquet/`
- `mimic-iv/concepts_fhir/concepts/demographics/icustay_detail/attempt_0002/shape.demo.json`

No implementation artifacts, notes, carryover, or commits were modified.
