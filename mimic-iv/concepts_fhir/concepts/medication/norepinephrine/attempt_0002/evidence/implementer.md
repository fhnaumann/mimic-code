# Implementer evidence — norepinephrine attempt_0002

The implementer read the canonical source SQL, the reusable source analysis and
FHIR probe carryover, the full oracle manifest entry, `MIMIC_NOTES.md`, and the
relevant provisional ICU medication fragments. The reopened instruction was
applied: the output retains the six oracle columns and adds the opaque
`icu_encounter_key` and `patient_key` columns required by downstream
SQL-on-FHIR consumers.

The implementation uses the exact ICU medication coding system and code
`221906`, joins the ICU Encounter view by opaque reference/resource key,
recovers `stay_id` from the ICU identifier value, emits a typed NULL INTEGER
for unrepresentable `linkorderid`, preserves both effective[x] variants, casts
FHIR quantities to numeric values, and uses `TRY_CAST(... AS TIMESTAMP_NTZ)`
for wall-clock datetimes. It does not parse or reconstruct resource IDs.

Artifacts produced once in this attempt:

- `ViewDefinition.medication_administration.json`
- `ViewDefinition.encounter_icu.json`
- `concept.sql`
- `unrepresentable.json`

`uv run mimic_utils lint-sql norepinephrine` passed cleanly. A dataset-wide
finding that the ICU medication ETL trims dosage units before serialization was
appended to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/norepinephrine.md`.
