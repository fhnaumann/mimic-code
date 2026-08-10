# Implementer Evidence: `age` (attempt_0002)

**Stage:** concept-implementer (retry fix)
**Date:** 2026-08-07
**Concept:** demographics/age
**Diagnosis held:** attempt_0001 passed execution and all six column names but
failed the demo shape gate because `subject_id` and `hadm_id` were VARCHAR
(identifier.value is a STRING) against INTEGER in the manifest.

## Fix applied

Separated FHIR UUID join keys from MIMIC identifier values, and cast the
identifier strings to INTEGER:

- `subject_id`: `CAST(subject_id_str AS INTEGER)`
- `hadm_id`: `CAST(hadm_id_str AS INTEGER)`
- `admittime`: `CAST(period.start AS TIMESTAMP_NTZ)`
- `anchor_age`: `CAST(NULL AS SMALLINT)` (typed NULL — unrepresentable)
- `anchor_year`: `CAST(NULL AS SMALLINT)` (typed NULL — unrepresentable)
- `age`: `CAST(CAST(YEAR(admittime) - YEAR(birthDate) AS INTEGER) AS BIGINT)`
  (year subtraction, per MIMIC_NOTES; BIGINT matches manifest)

ViewDefinitions project Patient token keys/identifier/birthDate and hosp
Encounter key/period, join through FHIR resource keys, filtered to the
`encounter-hosp` identifier system.

## Manifest check (oracle/oracle_manifest.full.json)

subject_id INTEGER, hadm_id INTEGER, admittime TIMESTAMP, anchor_age SMALLINT,
anchor_year SMALLINT, age BIGINT. Key: hadm_id. All six output columns match
the manifest types.

## MIMIC_NOTES.md entries that changed mapping

- "Patient.birthDate encodes the anchor pair" → year subtraction for age.
- "MIMIC ids live in identifier.value as STRINGs" → INTEGER casts.
- "FHIR datetimes carry an offset — cast to TIMESTAMP_NTZ".
- "Encounter has three identifier systems" → hosp filter.
- "Unrepresentable columns: emit NULL" → typed NULLs + unrepresentable.json.
- "Extensions are not a column" → no anchor extension on Patient.

**MIMIC_NOTES.md updated: none** (all findings confirmed existing entries).

## Artifacts created (write-once, attempt_0002)

- ViewDefinition.patient.json
- ViewDefinition.encounter.json
- concept.sql
- unrepresentable.json
