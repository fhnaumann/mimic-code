Evidence block — `first_day_bg_art`, attempt `0001`.

Created `ViewDefinition.icu_encounter.json`, `ViewDefinition.patient.json`, and `concept.sql` in the immutable attempt directory. The ViewDefinitions project ICU Encounter resource key, patient reference key, ICU stay identifier, and period start, plus the Patient identifier spine. The SQL consumes the completed dependency as unqualified `bg`, preserves the source LEFT JOIN, `specimen = 'ART.'` predicate, inclusive six-hours-before/one-day-after window, ICU-stay grouping, and all MIN/MAX output columns. Numeric identifier strings are cast to INTEGER; FHIR datetimes use `TRY_CAST(... AS TIMESTAMP_NTZ)`; resource keys remain opaque and verbatim.

`uv run mimic_utils lint-sql first_day_bg_art` and `git diff --check` both passed. No `unrepresentable.json` was needed and no new dataset-wide quirk was established, so no notes fragment entry was appended.
