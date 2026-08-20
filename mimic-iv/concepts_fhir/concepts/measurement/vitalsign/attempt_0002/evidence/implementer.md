# Implementer evidence — vitalsign, attempt 0002

The implementer read the canonical `mimic-iv/concepts/measurement/vitalsign.sql`, the reusable source and FHIR analyses, the manifest, the canonical ViewDefinition example, `MIMIC_NOTES.md`, and the current fragments. It applied exact itemid/code-system filters, identifier-spine joins, opaque resource-key handling, Quantity casting, bounded `VARCHAR`, and `TIMESTAMP_NTZ` guidance.

Written artifacts:

- `ViewDefinition.vitalsign_observation.json`
- `ViewDefinition.vitalsign_patient.json`
- `ViewDefinition.vitalsign_icu_encounter.json`
- `concept.sql`

The SQL preserves the 15 manifest columns and adds `patient_key` and `icu_encounter_key`, applies all 19 source itemids and predicates, pivots by recovered numeric identifiers and effective time, and uses equality joins for resource keys. `uv run mimic_utils lint-sql vitalsign` reported clean. No `unrepresentable.json` was needed and no new dataset-wide finding was reported.
