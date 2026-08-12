# Concept implementer evidence

Concept: `crrt`; attempt: `0005`.

## Evidence

- Read the canonical CRRT SQL, `MIMIC_NOTES.md`, the CRRT carryover source analysis and FHIR probe, and the reopened-attempt instruction.
- Authored Observation and ICU Encounter ViewDefinitions using the exact chartevents coding system, identifier-based ICU stay join, repeated Observation preservation, and Quantity/string projections.
- Authored `concept.sql` with explicit manifest-compatible casts and bare `TRY_CAST(... AS TIMESTAMP_NTZ)` datetime handling as required by the reopen instruction.
- Both ViewDefinitions passed JSON validation.
- `uv run mimic_utils lint-sql crrt` result: clean.

Artifacts:

- `ViewDefinition.crrt_observation.json`
- `ViewDefinition.crrt_encounter.json`
- `concept.sql`

No `unrepresentable.json` was needed and no dataset-wide notes fragment was appended.
