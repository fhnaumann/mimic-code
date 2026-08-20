# Evidence — concept-implementer

Concept `nsaid`, attempt `0002`.

Read the reusable source/FHIR analyses, canonical SQL, curated
`MIMIC_NOTES.md`, all existing fragments, and the reopened resource-key
instruction. Authored fresh Patient, hospital Encounter, MedicationRequest,
name-bearing Medication, medication-mix, and medication-mix ingredient
ViewDefinitions plus `concept.sql`. The port preserves all 20 source NSAID
literals, direct/mix `UNION ALL` multiplicity, hospital-Encounter filtering,
paired opaque resource keys, bounded string casts, and `TIMESTAMP_NTZ` parsing.

`uv run mimic_utils lint-sql nsaid` passed and JSON validation passed. No
`unrepresentable.json` was added and no new dataset-wide note was appended.

Artifacts:
- `ViewDefinition.encounter.json`
- `ViewDefinition.medication.json`
- `ViewDefinition.medication_mix.json`
- `ViewDefinition.medication_mix_ingredient.json`
- `ViewDefinition.medication_request.json`
- `ViewDefinition.patient.json`
- `concept.sql`
