Evidence block

Concept: `complete_blood_count`; attempt: `0003`.

Created:
- `ViewDefinition.lab_observation.json`
- `ViewDefinition.patient.json`
- `ViewDefinition.specimen.json`
- `ViewDefinition.encounter.json`
- `concept.sql`

The implementation projects Observation, Patient, Specimen, and hospital Encounter resources; filters the lab system and exact ten itemids, excludes comparator-synthesized values, retains positive numeric values, left-joins Encounter, groups by `specimen_id`, and applies MAX pivots. All manifest columns are explicitly cast, with opaque `patient_key`, `encounter_key`, and `specimen_key` retained as paired resource keys.

Read the source/prober carryover, complete MIMIC notes, and all provisional fragments. Applied the identifier-spine, opaque-key, specimen-spine, incomplete-Encounter-reference, exact-code, Quantity-cast, polymorphic-effective, and `TIMESTAMP_NTZ` datetime guidance. The CBC comparator fragment was verified against the cited ETL and Delta/DuckDB probe. No new fragment entry was appended.

`uv run mimic_utils lint-sql complete_blood_count` passed cleanly. All four ViewDefinitions are valid JSON; the attempt contains only the five newly created implementation artifacts. No `unrepresentable.json` was justified. Known caveats are intrinsic DST-normalized lab times, nullable `hadm_id` where Encounter references are absent, and possible full-data comparator-synthesized Quantity rows.
