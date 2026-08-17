Evidence block

Concept: `creatinine_baseline`, attempt `0002`.

Artifacts:
- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.condition.json`
- `concept.sql`

The candidate consumes `FROM age` and `FROM chemistry`, joins Patient gender by identifier value, and derives CKD through Condition-to-hospital-Encounter joins. All seven manifest columns are explicitly cast in order. Resource keys are used only for joins; no key is emitted. No old observation/specimen ViewDefinitions or `unrepresentable.json` were created.

Applied curated notes on identifier spines, opaque resource IDs, hospital Encounter filtering, Condition diagnosis backbones, bounded Spark `VARCHAR` casts, and dependency representation loss. Read and reconciled fragments `creatinine_baseline.md`, `chemistry.md`, and `kdigo_creatinine.md`; no new dataset-wide quirk was discovered or appended.

`uv run mimic_utils lint-sql creatinine_baseline` passed: SQL clean.
