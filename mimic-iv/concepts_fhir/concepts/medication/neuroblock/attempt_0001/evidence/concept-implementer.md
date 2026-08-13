# Concept-implementer evidence — neuroblock

Read the source and FHIR carryover analyses, LOOP_CONTRACT.md, MIMIC_NOTES.md,
the neuroblock fragment, and the oracle manifest. Created the immutable
ViewDefinitions, Spark SQL, and unrepresentability declaration in this attempt.
The implementation filters exact medication system/codes, joins ICU Encounter
identifiers by opaque reference equality, casts Quantity values to FLOAT and
FHIR datetimes to TIMESTAMP_NTZ, and emits typed NULL for the unavailable
orderid. The declaration records that orderid is the manifest key and may be
essential, leaving that decision to the full comparator and equivalence judge.

Created:
- `ViewDefinition.medication_administration.json`
- `ViewDefinition.encounter_icu.json`
- `concept.sql`
- `unrepresentable.json`

`uv run mimic_utils lint-sql neuroblock` passed. No commit was made.
