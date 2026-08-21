# Concept-implementer evidence — sirs, attempt_0001

The implementer read the canonical SIRS SQL, both carryover analyses, the
manifest, curated notes, relevant fragments, and the ViewDefinition/Pathling
authoring conventions. It created three resource views for the Patient, ICU
Encounter, and hospital Encounter identity spine, plus `concept.sql`.

The candidate consumes only the three preprocessed dependency views and the
three authored resource labels. It joins dependencies by opaque
`icu_encounter_key`, preserves the source's left joins and ordered CASE
branches, casts all manifest value columns to `INTEGER`, and emits the three
required type-prefixed resource keys unchanged. No resource IDs were parsed or
reconstructed, and no unrepresentable declaration was needed.

`uv run mimic_utils lint-sql sirs` was clean. Artifacts produced once in this
attempt:

- `ViewDefinition.patient.json`
- `ViewDefinition.icu_encounter.json`
- `ViewDefinition.encounter.json`
- `concept.sql`
