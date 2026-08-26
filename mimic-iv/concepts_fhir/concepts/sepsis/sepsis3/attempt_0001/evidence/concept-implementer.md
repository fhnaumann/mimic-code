Concept `sepsis3`; implementation stage for attempt_0001.

Read the source and FHIR carryover analyses, the full `MIMIC_NOTES.md`, all
existing `MIMIC_NOTES.d/*.md` fragments, completed dependency attempts,
canonical SQL, and the oracle manifest. Applied the identifier/key,
Encounter-system, opaque-id, dependency-boundary, and `TIMESTAMP_NTZ` rules.

Authored once:
- `ViewDefinition.icu_encounter.json`
- `ViewDefinition.patient.json`
- `concept.sql`

The candidate consumes only the completed `sofa` and
`suspicion_of_infection` dependency views, uses opaque resource keys for
equality joins and required key outputs, preserves the SOFA threshold,
inclusive `[-48,+24]` join, per-stay ordering, Boolean derivation, and the 14
manifest columns/types plus `icu_encounter_key`/`patient_key`. No
`unrepresentable.json` was needed. No resource ids were parsed, regenerated,
hashed, hardcoded, or used for semantic inference.

`uv run mimic_utils lint-sql sepsis3` completed cleanly. No new dataset-wide
quirk was found and no additional fragment entry was appended.
