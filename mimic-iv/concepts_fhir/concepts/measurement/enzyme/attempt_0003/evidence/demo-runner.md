# Demo runner evidence — enzyme attempt 0003

- `uv run mimic_utils run-demo enzyme` executed embedded Pathling on Spark successfully, registered the four ViewDefinitions, and produced 1,411 candidate rows.
- Shape gate result: `shape_ok`; all 15 manifest columns were present, types were compatible (`int`, `timestamp_ntz`, `double`), and no execution errors occurred.
- The three extra columns (`patient_key`, `encounter_key`, `specimen_key`) are the manifest-declared key columns; no required key column was missing. Row count was recorded but was not a gate.
- Artifacts: `shape.demo.json` and `candidate.demo.parquet/` in `mimic-iv/concepts_fhir/concepts/measurement/enzyme/attempt_0003/`.
