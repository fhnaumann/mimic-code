# Concept implementer evidence — `first_day_sofa`

## Artifacts

- `ViewDefinition.patient.json`
- `ViewDefinition.hospital_encounter.json`
- `ViewDefinition.icu_encounter.json`
- `concept.sql`

## Findings

- The ICU Encounter ViewDefinition selects only the `encounter-icu` identifier stream and exposes opaque ICU, hospital, and patient reference keys, ICU identifier value, and `period.start`.
- The hospital Encounter ViewDefinition exposes the hospital Encounter resource key and the exact hospital identifier system/value.
- The Patient ViewDefinition exposes the Patient resource key and patient identifier value.
- `concept.sql` consumes all ten completed dependency stems and joins each by the published opaque ICU encounter key. It preserves the canonical inclusive windows, `ART.` specimen filter, `InvasiveVent` status filter, SOFA score branches, and required final resource-key columns.
- Every manifest value column is explicitly cast; FHIR datetime parsing uses bare `TRY_CAST(... AS TIMESTAMP_NTZ)`. No resource id is parsed or reconstructed.
- No `unrepresentable.json` was needed and no new dataset-wide quirk was established; `MIMIC_NOTES.d/first_day_sofa.md` was not changed.

## Evidence block

Read/checks: read `AGENTS.md`, `LOOP_CONTRACT.md`, the complete `MIMIC_NOTES.md`, relevant fragments, canonical SQL, manifest entry, both first_day_sofa carryover analyses, completed dependency states/output shapes, and dependency identifier-stripping logic. Authored the four listed artifacts once in this attempt and ran SQL lint successfully: `sql-lint: first_day_sofa: clean`. No prior attempt, state file, curated notes, or commit was modified.
