# Demo runner evidence — arb attempt 0005

The replayed attempt's carried ViewDefinitions and `concept.sql` were read but
not modified. `uv run mimic_utils run-demo arb` executed successfully with
embedded Pathling on Spark. The shape artifact reports `shape_ok`: the
candidate columns and compatible types match the oracle manifest; the extra
`encounter_key` and `patient_key` columns are the manifest-required FHIR
identity key columns. The demo returned 35 rows, which is observational only
and was not used as a correctness gate.

Produced artifacts:

- `candidate.demo.parquet`
- `shape.demo.json`

No dataset-wide quirk was discovered or appended to `MIMIC_NOTES.d/arb.md`.
