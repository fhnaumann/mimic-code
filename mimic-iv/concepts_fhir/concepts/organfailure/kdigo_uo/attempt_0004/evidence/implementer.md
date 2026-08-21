# Implementer evidence — kdigo_uo attempt 0004

Concept: `kdigo_uo`; attempt: `0004`.

Created:
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0004/ViewDefinition.icu_encounter.json`
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0004/concept.sql`

The ICU Encounter projection emits opaque encounter/patient keys, ICU identifier values, and `period.start`. SQL consumes `urine_output` and `weight_durations`, preserving joins, windows, half-open intervals, NULL behavior, manifest column order/types, and verbatim key columns. Exactly six precision casts changed from `DECIMAL(38,12)` to `DECIMAL(38,9)`.

Lint: `uv run mimic_utils lint-sql kdigo_uo` passed cleanly.

Read the canonical SQL, manifest, carryover analyses, `MIMIC_NOTES.md`, and relevant fragments. Applied identifier-spine, opaque-key, ICU identifier-system, `TIMESTAMP_NTZ`/DST, dependency-boundary, and Quantity/choice-field guidance. No new fragment entry was appended; `MIMIC_NOTES.md` was not modified.
