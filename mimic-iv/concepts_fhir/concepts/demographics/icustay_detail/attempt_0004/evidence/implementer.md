# Implementer evidence — `icustay_detail`, attempt 0004

- Read the reusable source analysis and FHIR probe mapping, the canonical source SQL, the oracle manifest, `MIMIC_NOTES.md`, and the concept fragment.
- Applied the reopened resource-key requirement: the final SQL emits `patient_key`, `encounter_key`, and `icu_encounter_key` beside the integer MIMIC identifiers while using opaque keys only for equality joins.
- Produced fresh ViewDefinitions for Patient, hospital Encounter, and ICU Encounter, plus `concept.sql` and `unrepresentable.json`.
- Implemented identifier-system stream filtering, ICU `partOf` joining, Patient/Encounter key joins, `TIMESTAMP_NTZ` datetime handling, LOS/rank calculations, race best-effort mapping, and typed-NULL `hospital_expire_flag`.
- `uv run mimic_utils lint-sql icustay_detail` passed cleanly.
- No new dataset-wide quirk was discovered; no `MIMIC_NOTES.d/icustay_detail.md` entry was appended.

Artifacts:

- `ViewDefinition.icustay_detail_patient.json`
- `ViewDefinition.icustay_detail_hospital_encounter.json`
- `ViewDefinition.icustay_detail_icu_encounter.json`
- `concept.sql`
- `unrepresentable.json`
