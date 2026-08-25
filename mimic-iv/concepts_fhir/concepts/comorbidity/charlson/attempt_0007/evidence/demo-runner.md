# Demo runner evidence

## Concept and attempt

- Concept: `charlson`
- Attempt: `attempt_0007`
- This is a replayed attempt; the SQL and ViewDefinitions were carried forward
  byte-identically from attempt 0006 and were not edited.

## Checks

- Command: `uv run mimic_utils run-demo charlson`
- Engine: embedded Pathling on Spark over the demo Delta warehouse.
- Execution: succeeded.
- Shape verdict: `shape_ok`.
- All 21 oracle columns were present with compatible integer types; no missing
  or incompatible columns.
- Required resource key columns `patient_key` and `encounter_key` were present.
- Demo row count was 275; reported only and not used as a correctness gate.

## Result

The cheap demo shape gate passed. This permits a full-data run but provides no
correctness claim. No SQL or ViewDefinition was changed.

## Artifacts

- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0007/shape.demo.json`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0007/candidate.demo.parquet`
