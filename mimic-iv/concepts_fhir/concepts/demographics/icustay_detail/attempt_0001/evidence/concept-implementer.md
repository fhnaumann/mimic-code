## Evidence

Implemented `icustay_detail` attempt 0001 after reading the source SQL,
oracle manifest, `AGENTS.md`, complete `MIMIC_NOTES.md`, existing notes
fragments, carryover analyses, and prior attempt evidence.

The implementation uses Patient, hospital Encounter, and ICU Encounter
ViewDefinitions with identifier-system filtering and UUID-only joins. The
18-column Spark SQL preserves the manifest schema and source semantics with
explicit casts, bounded `VARCHAR`, `TIMESTAMP_NTZ`, LOS/rank derivations,
gender/race normalization, and LEFT joins. No `unrepresentable.json` was
needed.

Static validation covered JSON structure and labels, Spark SQL parsing,
manifest column order/types, and outer casts. Demo execution was not run by
the implementer. Identifier-spine, Encounter-stream, extension, birthDate,
datetime, and bounded-VARCHAR notes were applied. The existing race-loss
fragment was used; no new notes section was appended.

Artifacts created once:

- `ViewDefinition.icustay_detail_patient.json`
- `ViewDefinition.icustay_detail_hospital_encounter.json`
- `ViewDefinition.icustay_detail_icu_encounter.json`
- `concept.sql`

All artifacts are under
`mimic-iv/concepts_fhir/concepts/demographics/icustay_detail/attempt_0001/`.
Known caveats are lossy race normalization, transformed FHIR `birthDate` for
admission age, and possible upstream DST timestamp normalization.
