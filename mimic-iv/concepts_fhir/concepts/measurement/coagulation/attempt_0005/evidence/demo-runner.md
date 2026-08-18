# Demo runner evidence — coagulation attempt 0005

Ran `uv run mimic_utils run-demo coagulation` with embedded Pathling 9.6.0 on
Spark 4.0.2 over the local demo Delta warehouse. The four ViewDefinitions were
registered as Spark temporary views and `concept.sql` executed successfully.

Result: `shape_ok` (exit 0). All ten manifest column names and types matched;
the three additional `patient_key`, `encounter_key`, and `specimen_key`
columns are required manifest key columns and were accepted. Candidate demo
row count was 1,630; this was reported only and not gated.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/measurement/coagulation/attempt_0005/candidate.demo.parquet/`
- `mimic-iv/concepts_fhir/concepts/measurement/coagulation/attempt_0005/shape.demo.json`

No execution or schema errors occurred. A repeated run was refused by the
write-once guard, so the first successful run is authoritative.
