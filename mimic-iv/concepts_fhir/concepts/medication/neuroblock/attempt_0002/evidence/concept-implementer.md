Evidence block:

Concept: neuroblock
Attempt: 0002

Produced:
- `ViewDefinition.medication_administration.json`
- `ViewDefinition.encounter_icu.json`
- `concept.sql`
- `unrepresentable.json`

The port projects ICU MedicationAdministration data, filters the exact ICU medication system and codes 222062/221555, requires non-null rate, joins ICU Encounter resources by opaque reference-key equality, and recovers stay_id from the ICU Encounter identifier. Quantity values are numerically cast; datetimes use TRY_CAST(... AS TIMESTAMP_NTZ). All manifest columns are explicitly cast in order.

orderid is emitted as typed NULL and declared unrepresentable because it has no independent FHIR serialization. The supplied representable clinical grain (stay_id, starttime, endtime) was incorporated. No terminal blocking decision was made.

Read and applied LOOP_CONTRACT.md, MIMIC_NOTES.md, the neuroblock carryover analyses, the canonical ViewDefinition example, and relevant medication/ICU fragments. No new dataset-wide quirk was established, so MIMIC_NOTES.d/neuroblock.md was not appended.

Validation: JSON syntax checks passed and `uv run mimic_utils lint-sql neuroblock` reported clean.
