Evidence

Concept: epinephrine; attempt: 0003.

Created:
- `mimic-iv/concepts_fhir/concepts/medication/epinephrine/attempt_0003/ViewDefinition.medication_administration.json`
- `mimic-iv/concepts_fhir/concepts/medication/epinephrine/attempt_0003/ViewDefinition.encounter_icu.json`
- `mimic-iv/concepts_fhir/concepts/medication/epinephrine/attempt_0003/concept.sql`
- `mimic-iv/concepts_fhir/concepts/medication/epinephrine/attempt_0003/unrepresentable.json`

The MedicationAdministration view filters ICU medication coding system plus code `221289`, projects both effective[x] variants, Quantity values, and opaque join keys. The ICU Encounter view projects the `encounter-icu` identifier. SQL preserves the six manifest columns, casts each explicitly, coalesces end-time variants, emits typed-NULL `linkorderid`, and adds `patient_key`/`icu_encounter_key`.

Read the source and both carryover analyses, the full `MIMIC_NOTES.md`, canonical ViewDefinition example, and all `MIMIC_NOTES.d` fragments. Applied the identifier-spine, opaque-resource-key, ICU identifier-system, polymorphic-choice, Quantity-string, and TIMESTAMP_NTZ notes. Epinephrine fragment claims were verified by its authoritative Delta probe; other fragments were treated as provisional leads. No new fragment entry was appended.

Artifact JSON/SQL parsing passed. `uv run mimic_utils lint-sql epinephrine` passed cleanly. No commit made.
