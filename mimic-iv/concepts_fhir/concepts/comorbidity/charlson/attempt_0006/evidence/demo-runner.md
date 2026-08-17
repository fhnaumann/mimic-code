## Demo shape gate — `charlson` attempt 0006

`uv run mimic_utils run-demo charlson` executed cleanly against the local demo Delta warehouse via embedded Pathling on Spark. It registered `age`, `condition`, `encounter`, and `patient`, materialised the ViewDefinitions, ran `concept.sql`, wrote candidate Parquet, and completed the shape gate.

- Execution: succeeded (`executed: true`); no error output.
- Columns: all 21 oracle columns present; the two additional columns `patient_key` and `encounter_key` are the manifest-declared key columns. `missing_key_columns: []`, `unexpected_columns: []`, `schema.match: true`.
- Types: compatible for all 21 oracle columns; `incompatible_types: []`.
- Row count: 275, informational only and not gated.
- Verdict: `shape_ok`; may proceed to full data.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0006/candidate.demo.parquet`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0006/shape.demo.json`

The demo pass is a shape gate only and is not evidence of full-data correctness.
