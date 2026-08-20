# Implementation evidence — vasopressin attempt 0002

The concept implementer reused the source analysis and FHIR probe carryover,
read `MIMIC_NOTES.md` and all `MIMIC_NOTES.d/*.md` fragments, and treated
sibling fragments as provisional leads. It authored:

- `ViewDefinition.medication_administration.json`
- `ViewDefinition.encounter_icu.json`
- `concept.sql`
- `unrepresentable.json`

The implementation filters the ICU MedicationAdministration stream by the
exact MIMIC medication system and code `222315`, joins the opaque encounter
reference key to the ICU Encounter view, projects both effective[x] variants,
casts Quantity aliases before arithmetic, uses `TIMESTAMP_NTZ`, emits typed
NULL `linkorderid`, and retains `icu_encounter_key` and `patient_key` as
required key columns. No resource-id inversion was used. The implementer ran
`uv run mimic_utils lint-sql vasopressin`; lint was clean. No existing attempt
artifact was overwritten and no new dataset-wide note was appended.
