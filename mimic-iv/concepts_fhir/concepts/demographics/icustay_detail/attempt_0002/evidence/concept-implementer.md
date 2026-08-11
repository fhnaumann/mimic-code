## Evidence

Implemented corrected `icustay_detail` attempt 0002 without modifying attempt
0001, notes, carryover, or running the demo.

Created:

- `ViewDefinition.icustay_detail_patient.json`
- `ViewDefinition.icustay_detail_hospital_encounter.json`
- `ViewDefinition.icustay_detail_icu_encounter.json`
- `concept.sql`
- `unrepresentable.json`

The Patient projection now carries race/ethnicity OMB codings and the SQL
decodes the full supported categories. Hospital and ICU Encounter projections
retain identifier-system filters, UUID-only joins, timestamps, LOS, ranks, and
all 18 manifest columns with explicit casts. `hospital_expire_flag` is a typed
NULL with a declaration that the source flag and admission death time are not
serialized in FHIR. Admission age and DST-normalized timestamp caveats remain
intrinsic upstream transformations.

Static JSON, Spark SQL parsing, manifest-order/type/cast, and whitespace
validation passed. No dataset notes fragment was appended or changed.
