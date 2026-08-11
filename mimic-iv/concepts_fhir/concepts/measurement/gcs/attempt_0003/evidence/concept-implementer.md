# Concept implementer evidence — `gcs`

- Concept: `gcs`; attempt: `0003`.
- Read/checked: reusable source/FHIR analyses, attempt-0002 diagnosis and artifacts, canonical GCS SQL, `MIMIC_NOTES.md`, and all notes fragments.
- Created once: `ViewDefinition.gcs_observation.json`, `ViewDefinition.gcs_encounter.json`, `ViewDefinition.gcs_patient.json`, and `concept.sql`.
- Correction: SQL uses UUIDv5 matching over the finite GCS `(itemid,value)` vocabulary at served and one-hour-earlier times to restore source charttime before pivoting, while preserving genuine 03:xx rows and identifying `No Response-ETT` only by the UUID witness. It retains the canonical six-hour preceding-row logic and typed manifest-shaped output.
- Checks: JSON parsing passed; corrected SQL matched the demo oracle with `3,279` rows and zero missing, extra, or conflicting rows. No `unrepresentable.json` was needed.
- Notes: no new dataset-wide fragment entry was appended. No prior artifact was edited and no commit/state transition was made.
