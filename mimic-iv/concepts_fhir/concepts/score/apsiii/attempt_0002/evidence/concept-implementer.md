Evidence block from concept-implementer

Concept: `apsiii`, attempt `0002`.

Created:
- `ViewDefinition.patient.json`
- `ViewDefinition.icu_encounter.json`
- `ViewDefinition.hospital_encounter.json`
- `ViewDefinition.condition.json`
- `concept.sql`

The SQL uses the ICU Encounter as the left spine, opaque-key joins to all six
completed dependencies, hospital-linked Condition ICD filters, canonical APS
III scoring, preserved null behavior, and manifest-ordered explicit casts. No
`unrepresentable.json` was emitted; the completed `first_day_gcs` dependency
supplies `gcs_unable`, so the old GCS gap was not propagated.

The implementer read the canonical SQL, manifest, `AGENTS.md`,
`LOOP_CONTRACT.md`, both APSIII carryover files, `MIMIC_NOTES.md`, and relevant
provisional fragments. It applied identifier-spine/resource-key,
Encounter-system, datetime/`TIMESTAMP_NTZ`, dependency-boundary, and current
proprietary Condition-system guidance. APSIII/SAPSII Condition claims and
rebuilt GCS behavior were verified by the reused prober/current dependency
state; other provisional fragment claims were treated as leads and not
independently promoted.

Check: `uv run mimic_utils lint-sql apsiii` completed cleanly. No demo
validation or terminal semantic verdict was performed. No dataset-wide note
was appended by this stage.
