Evidence block — chemistry, attempt_0003

Created `ViewDefinition.lab_observation.json`, `ViewDefinition.patient.json`, `ViewDefinition.encounter.json`, `ViewDefinition.specimen.json`, and `concept.sql` in `mimic-iv/concepts_fhir/concepts/measurement/chemistry/attempt_0003/`.

The implementation reuses the validated source and FHIR carryover analyses, preserves all twelve itemids, specimen grouping, MAX pivots, nullable `hadm_id` via LEFT JOIN, and explicit manifest casts. It fixes the attempt_0002 bug by removing the native instant projection and casting the FHIR dateTime and Period string variants separately to `TIMESTAMP_NTZ` before `COALESCE`, preserving wall-clock semantics and only the known narrow upstream DST gap.

Read and applied `AGENTS.md`, `LOOP_CONTRACT.md`, canonical SQL, attempt_0002 artifacts and diagnosis, manifest, carryover analyses, `MIMIC_NOTES.md`, and all notes fragments. No notes fragment was appended and no prior attempt or `MIMIC_NOTES.md` was edited.

Artifacts: `mimic-iv/concepts_fhir/concepts/measurement/chemistry/attempt_0003/ViewDefinition.*.json`; `mimic-iv/concepts_fhir/concepts/measurement/chemistry/attempt_0003/concept.sql`.
