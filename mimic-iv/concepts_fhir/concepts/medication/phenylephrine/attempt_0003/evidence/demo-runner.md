# Demo runner evidence

- Concept: `phenylephrine`
- Attempt: `0003`
- Read: the frozen implementation artifacts and demo shape contract.
- Checked: embedded Pathling on Spark execution, manifest column names and compatible types, and required key columns.
- Result: `shape_ok`; execution succeeded. The six manifest columns matched, `patient_key` and `icu_encounter_key` were present as required key columns, and all types were compatible. Demo produced 625 rows; row count was observed only and not gated against the 193,260-row full oracle.
- Artifacts: `candidate.demo.parquet`, `shape.demo.json`.
- Dataset-wide notes: no new quirk identified or appended; `MIMIC_NOTES.md` was not modified.
