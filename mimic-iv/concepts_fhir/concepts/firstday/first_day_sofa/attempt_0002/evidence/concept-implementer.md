# Concept implementer evidence — `first_day_sofa` attempt 0002

## Result

- Reused `carryover/first_day_sofa/source-analyst.md` and `fhir-prober.md`; no analysis stage was rerun or invalidated.
- Authored fresh copies of `ViewDefinition.patient.json`, `ViewDefinition.hospital_encounter.json`, `ViewDefinition.icu_encounter.json`, and `concept.sql` in attempt 0002.
- Preserved the canonical SOFA derivation, all ten dependency boundaries, opaque-key joins, windows, filters, and OR logic.
- Changed only the four cardiovascular `0.1` threshold literals to `CAST(0.1 AS FLOAT)` to avoid Spark promotion of published FLOAT values.
- Preserved dopamine `> 5`; did not add an epsilon, use ids, or attempt to recover the known six-decimal upstream precision loss.
- `uv run mimic_utils lint-sql first_day_sofa` passed cleanly. No `unrepresentable.json` or notes fragment was added.

## Evidence block

Read/checks: read `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, all existing fragments as provisional, both carryover analyses, the manifest entry, and attempt 0001 artifacts. Authored the four attempt-0002 artifacts once and ran SQL lint successfully. No files outside attempt 0002 were edited and no commit was made.
