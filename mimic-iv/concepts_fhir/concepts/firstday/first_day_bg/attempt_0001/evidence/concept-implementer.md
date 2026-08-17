Evidence block — concept-implementer

Concept `first_day_bg`, attempt `0001`.

Read source/prober carryover, the completed `bg` attempt and carryover, `MIMIC_NOTES.md`, and provisional fragments `chemistry.md`, `coagulation.md`, `complete_blood_count.md`, `blood_differential.md`, `cardiac_marker.md`, and `icustay_times.md`. Applied identifier-spine, ICU identifier-system, opaque-ID, and `TIMESTAMP_NTZ` notes.

Produced:
- `mimic-iv/concepts_fhir/concepts/firstday/first_day_bg/attempt_0001/ViewDefinition.patient.json`
- `mimic-iv/concepts_fhir/concepts/firstday/first_day_bg/attempt_0001/ViewDefinition.icu_encounter.json`
- `mimic-iv/concepts_fhir/concepts/firstday/first_day_bg/attempt_0001/concept.sql`

The views project Patient identifiers and ICU Encounter identifiers, use opaque reference equality joins, and project `period.start`. The SQL consumes the unqualified `bg` dependency view, applies the inclusive 6-hour-before/1-day-after LEFT JOIN, groups by `(subject_id, stay_id)`, and emits all 44 manifest columns with explicit declared-type casts. No unrepresentable declaration was required, no notes fragment was appended, and no commit was made.

Lint result: `sql-lint: first_day_bg: clean`.
