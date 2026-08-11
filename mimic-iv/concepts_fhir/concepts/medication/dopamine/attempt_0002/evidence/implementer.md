# Implementer evidence — dopamine attempt_0002

Read the reusable source analysis and FHIR probe for `dopamine`, the loop contract, curated MIMIC notes, and the reopen history in the controller state. The implementation preserves the manifest's six output columns and `(stay_id, starttime)` comparison key, filters the exact ICU medication coding system plus code `221662`, recovers `stay_id` from the ICU Encounter identifier, emits typed NULL for unrepresentable `linkorderid`, casts Quantity values to FLOAT, and uses `TRY_CAST(... AS TIMESTAMP_NTZ)` for FHIR datetimes. The `linkorderid` declaration is recorded in `unrepresentable.json`.

Artifacts produced once in this attempt:

- `ViewDefinition.medication_administration.json`
- `ViewDefinition.encounter_icu.json`
- `concept.sql`
- `unrepresentable.json`

No existing attempt artifact was edited and no dataset-wide finding beyond the existing dopamine fragment was added.
