Evidence block — phenylephrine implementation

The implementation reads the medication-administration and ICU Encounter carryover mappings, `MIMIC_NOTES.md`, the relevant provisional fragments, `LOOP_CONTRACT.md`, and the Pathling/FHIR mapping conventions. It filters the exact ICU medication coding system and code `221749`, projects both effective[x] variants and Quantity rate/amount values, and joins Encounter by opaque reference-key equality to emit `stay_id`. `linkorderid` is emitted as typed NULL and documented in `unrepresentable.json`; no resource-id parsing or reconstruction is used.

Artifacts created once in attempt 0001:
- `ViewDefinition.medication_administration.json`
- `ViewDefinition.encounter_icu.json`
- `concept.sql`
- `unrepresentable.json`

`uv run mimic_utils lint-sql phenylephrine` passed. No new dataset-wide note was appended and no commit was made.
