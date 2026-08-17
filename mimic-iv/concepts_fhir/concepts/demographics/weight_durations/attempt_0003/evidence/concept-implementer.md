# Concept-implementer evidence

The implementer authored the fresh attempt artifacts:

- `ViewDefinition.weight_durations_observation.json`
- `ViewDefinition.weight_durations_icu_encounter.json`
- `concept.sql`

The implementation maps exact ICU chartevents codes `226512` and `224639`,
joins Observation encounter references to ICU Encounter resource keys by
opaque equality, obtains `stay_id` from the ICU identifier, casts Quantity
aliases before rounding, parses FHIR datetimes as `TIMESTAMP_NTZ`, preserves
the canonical windows, interval semantics, multiplicity, and `UNION ALL`, and
emits the required paired `icu_encounter_key` and `patient_key` columns at the
outer select. It does not parse or regenerate resource ids and does not try to
undo upstream DST normalization.

`uv run mimic_utils lint-sql weight_durations` passed cleanly. No
`unrepresentable.json` was needed and no new dataset-wide note was appended.
The implementer read the curated notes and relevant fragments, including the
opaque-key, exact-code, Quantity, datetime, ICU Encounter, and DST findings.
