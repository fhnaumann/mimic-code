# Evidence — concept-implementer

Concept: `arb`; attempt: `0004`.

Read the canonical `mimic-iv/concepts/medication/arb.sql`, the current oracle
manifest, `MIMIC_NOTES.md`, the `arb` carryover source analysis and FHIR probe,
and the canonical ViewDefinition example. Implemented the direct and
medication-mix ingredient branches with `UNION ALL`, all 16 source drug-name
predicates, hospital Encounter identifier filtering, explicit output casts,
and `TRY_CAST(... AS TIMESTAMP_NTZ)` for validity endpoints.

Created:

- `ViewDefinition.medication_request.json`
- `ViewDefinition.medication.json`
- `ViewDefinition.medication_mix.json`
- `ViewDefinition.medication_mix_ingredient.json`
- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `concept.sql`

The reopened resource-key instruction was applied: opaque `patient_key` and
`encounter_key` columns are retained beside the compared MIMIC identifier
columns at the outermost SELECT. No resource-id parsing, inversion,
regeneration, hashing, or hardcoding was used. No new dataset-wide quirk was
discovered, so `MIMIC_NOTES.d/arb.md` was unchanged.

Verification: `uv run mimic_utils lint-sql arb` passed cleanly.
