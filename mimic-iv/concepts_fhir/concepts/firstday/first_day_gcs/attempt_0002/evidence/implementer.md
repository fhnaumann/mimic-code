Evidence block

Concept: `first_day_gcs`, attempt 0002.

Created fresh immutable artifacts:

- `ViewDefinition.patient.json`
- `ViewDefinition.icu_encounter.json`
- `concept.sql`
- `unrepresentable.json`

The candidate reuses the source/FHIR carryover analysis and consumes `FROM gcs`. It preserves every ICU stay, the exact ICU identifier/key spine, inclusive `-6 HOURS` through `+1 DAY` window, and lowest-GCS/latest-charttime selection when unambiguous. It adds an ambiguity flag over the dependency rows in the window: a real dependency row with `gcs IS NULL` is the attempt-0006 ambiguity marker. When present, the target emits typed NULLs for `gcs_min`, `gcs_motor`, `gcs_verbal`, and `gcs_eyes` rather than selecting a known survivor; `gcs_unable` remains typed NULL and declared unrepresentable. No resource ID was parsed or regenerated.

`uv run mimic_utils lint-sql first_day_gcs` and JSON validation passed. Prior attempt, carryover, and notes fragments were not modified; no new dataset-wide quirk was established and no commit was made.
