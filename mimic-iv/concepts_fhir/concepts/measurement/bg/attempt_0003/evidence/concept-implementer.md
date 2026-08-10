# Concept implementation evidence

- Read: canonical `mimic-iv/concepts/measurement/bg.sql`, manifest, reusable `carryover/bg` analyses, `MIMIC_NOTES.md`, and attempt 0002 artifacts plus full-data diagnosis.
- Created once in attempt 0003: `ViewDefinition.patient.json`, `ViewDefinition.encounter.json`, `ViewDefinition.specimen.json`, `ViewDefinition.lab_observation.json`, `ViewDefinition.chart_observation.json`, and `concept.sql`.
- Preserved: the identifier spines, observation/specimen joins, proprietary code filters, specimen grouping, chart enrichment windows, and all 27 manifest columns with explicit output casts.
- Fixes: direct `CAST(COALESCE(...effective_datetime, ...effective_period_start) AS TIMESTAMP_NTZ)` without offset stripping/session-zoned parsing; chart quantities cast to `FLOAT` before FiO2 filtering, arithmetic, and aggregation; laboratory quantities remain `DOUBLE`; final FLOAT and DECIMAL output semantics retained.
- Result: implementation artifacts are ready for the demo shape gate. No `unrepresentable.json` is required. No carryover or `MIMIC_NOTES.md` entry was added or updated.
