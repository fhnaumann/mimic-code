# Evidence: concept-implementer (`first_day_bg`, attempt 0002)

Read `AGENTS.md`, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, the pathling-sql and
fhir-mapping skills, the canonical SQL, the prior attempt, and both reusable
carryover analyses. The reopened instruction was applied verbatim: the fresh
candidate retains the 44 manifest columns and now emits `patient_key` and
`icu_encounter_key` beside the corresponding MIMIC identifiers. The SQL
consumes the completed dependency through the unqualified `bg` view and does
not parse or reconstruct resource ids.

Created exactly once:

- `ViewDefinition.patient.json`
- `ViewDefinition.icu_encounter.json`
- `concept.sql`

`uv run mimic_utils lint-sql first_day_bg` passed cleanly. No new
dataset-wide quirk was discovered; `MIMIC_NOTES.d/first_day_bg.md` was not
modified by this stage.
