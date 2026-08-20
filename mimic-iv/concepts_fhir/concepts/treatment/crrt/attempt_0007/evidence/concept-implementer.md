Evidence block

Concept: `crrt`; attempt: `0007`.

Authored:
- `ViewDefinition.crrt_observation.json`
- `ViewDefinition.crrt_encounter.json`
- `concept.sql`

The port projects targeted chartevent Observations and ICU Encounters, filters
all 19 exact itemids/system values, preserves repeated `224146` rows before the
`(stay_id, charttime)` MAX pivot, coalesces FHIR effective-time variants, and
emits `icu_encounter_key` and `patient_key` alongside the manifest-shaped
columns. All declared columns have explicit casts.

`uv run mimic_utils lint-sql crrt` passed cleanly.

Read the curated `MIMIC_NOTES.md`, both CRRT carryover analyses, source SQL,
canonical ViewDefinition example, and all `MIMIC_NOTES.d/*.md` fragments. Applied
the identifier/key, opaque-resource-id, ICU identifier-system, categorical
`valueString`, Quantity alias, bounded `VARCHAR`, polymorphic datetime, and
`TIMESTAMP_NTZ`/DST notes. The CRRT fragment was treated as provisional;
repeated-row behavior was supported by reusable prober evidence, while its
UUID-recovery guidance was not used. No notes or fragments were modified, and
no new dataset-wide quirk was discovered.

Artifacts produced:
- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0007/ViewDefinition.crrt_observation.json`
- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0007/ViewDefinition.crrt_encounter.json`
- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0007/concept.sql`
