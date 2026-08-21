Evidence block

Concept: `first_day_gcs`, attempt 0001.

Created once in the immutable attempt directory:

- `ViewDefinition.patient.json`
- `ViewDefinition.icu_encounter.json`
- `concept.sql`
- `unrepresentable.json`

The ViewDefinitions use Patient/ICU Encounter identity keys, ICU identifier-system filtering, and ICU `period.start`. SQL consumes the completed `gcs` temp view, joins only on opaque encounter keys, preserves all ICU stays, applies the inclusive `-6 HOURS` / `+1 DAY` window and lowest-GCS/latest-charttime selection, emits manifest columns in order with explicit casts, and retains required opaque `patient_key` and `icu_encounter_key` companions. `gcs_unable` is typed NULL and declared unrepresentable; no No Response-ETT heuristic or resource-ID inversion was used.

JSON parsing, manifest/schema checks, and `uv run mimic_utils lint-sql first_day_gcs` passed. Curated notes and all provisional fragments were read; relevant leads were checked by the FHIR probe. No new dataset-wide quirk was established, so no notes fragment was appended by this stage. No existing attempt artifact was edited and no commit was made.
