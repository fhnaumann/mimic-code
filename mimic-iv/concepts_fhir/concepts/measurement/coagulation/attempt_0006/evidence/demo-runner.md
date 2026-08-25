## Evidence

- Read: `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json` and the replayed attempt artifacts.
- Checked: `uv run mimic_utils run-demo coagulation` using embedded Pathling on Spark; execution, column names, and type compatibility.
- Result: `shape_ok` / `match: true`; no missing or unexpected columns and no incompatible types. The three extra columns (`patient_key`, `encounter_key`, `specimen_key`) are required provenance key columns and are accepted by the shape gate. 1,630 demo rows were produced; row count is not a gate.
- Artifacts: `candidate.demo.parquet`, `shape.demo.json` under this attempt.
