# Evidence — concept-implementer

Concept `gcs`, attempt `0008`.

Authored `ViewDefinition.gcs_patient.json`, `ViewDefinition.gcs_encounter.json`, `ViewDefinition.gcs_observation.json`, and `concept.sql`. The implementation projects Patient and ICU Encounter keys, filters exact chartevents coding systems/codes, extracts component text for item `223900`, applies the canonical GCS pivot, six-hour carry-forward, defaults, ETT branch, eight manifest columns, and opaque `patient_key`/`icu_encounter_key` companions. No `unrepresentable.json` was created.

Read `AGENTS.md`, full `MIMIC_NOTES.md`, `LOOP_CONTRACT.md`, source-analysis and fhir-prober carryovers, manifest, and relevant fragments. Provisional claims were treated as leads; current GCS mappings were verified by the reusable rebuilt-warehouse probe. Applied curated coding, opaque-key, component-text, Quantity, and `TIMESTAMP_NTZ` rules. No fragment was appended.

`uv run mimic_utils lint-sql gcs` passed cleanly.
