# Implementer evidence — charlson attempt 0003

The concept implementer read the canonical Charlson SQL, the reusable source analysis and FHIR mapping carryover, `MIMIC_NOTES.md`, the provisional notes fragments, and the reopened resource-key instruction. It authored `ViewDefinition.condition.json`, `ViewDefinition.encounter.json`, `ViewDefinition.patient.json`, and `concept.sql` in this attempt, using opaque equality joins, the hospital Encounter identifier system, proprietary ICD systems, `FROM age`, paired resource-key output columns, and the canonical Charlson code tests/arithmetic.

`uv run mimic_utils lint-sql charlson` passed. The subsequent execution check found that the authored SQL is syntactically malformed: the age CTE has `SELECT` where `ag AS (` is required. Because attempt artifacts are write-once, no artifact was replaced. No notes fragment was appended.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0003/ViewDefinition.condition.json`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0003/ViewDefinition.encounter.json`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0003/ViewDefinition.patient.json`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0003/concept.sql`
