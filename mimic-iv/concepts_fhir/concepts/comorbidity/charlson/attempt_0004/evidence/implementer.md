# Implementer evidence — charlson attempt 0004

The implementer read `AGENTS.md`, both Charlson carryover analyses, the canonical `mimic-iv/concepts/comorbidity/charlson.sql`, the Charlson manifest entry, `MIMIC_NOTES.md`, the canonical ViewDefinition guidance, attempt 0003 artifacts, and all existing `MIMIC_NOTES.d/*.md` fragments. Provisional sibling fragments were treated as unverified. It authored fresh Condition, hospital Encounter, and Patient projections and a Spark SQL candidate using proprietary ICD systems, opaque equality joins, the completed `age` dependency, paired `patient_key`/`encounter_key` outputs, manifest integer casts, and canonical Charlson arithmetic.

Checks passed: JSON syntax validation, `uv run mimic_utils lint-sql charlson`, and embedded Spark demo execution (275 rows, 23 columns, shape OK). The SQL contains no resource-id parsing, regeneration, hashing, hardcoding, or physical-table re-derivation. No new dataset-wide quirk was found, so `MIMIC_NOTES.d/charlson.md` was unchanged.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0004/ViewDefinition.condition.json`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0004/ViewDefinition.encounter.json`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0004/ViewDefinition.patient.json`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0004/concept.sql`
