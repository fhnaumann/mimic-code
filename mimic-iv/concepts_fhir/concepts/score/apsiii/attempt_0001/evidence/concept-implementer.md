# Concept implementer evidence

Concept: `apsiii`, attempt `0001`.

The implementer read the canonical APS III SQL, both carryover analyses, LOOP_CONTRACT.md, MIMIC_NOTES.md, relevant fragments, and the ViewDefinition/pathling-SQL conventions. It created four immutable ViewDefinitions — `patient`, `hospital_encounter`, `icu_encounter`, and `condition` — and `concept.sql` under the attempt directory. The candidate consumes the six completed dependency temp views, preserves the source score CASE/window/join/null semantics and ICD filters, emits the manifest columns plus opaque `encounter_key`, `icu_encounter_key`, and `patient_key`, casts MIMIC identifier strings to integer output types, and uses `TIMESTAMP_NTZ` for timestamps. No resource ID was parsed or regenerated and no GCS heuristic was introduced.

`uv run mimic_utils lint-sql apsiii` completed cleanly and the ViewDefinition JSON files were validated. No `unrepresentable.json` was emitted and no new dataset-wide quirk was reported. Artifacts created: `ViewDefinition.patient.json`, `ViewDefinition.hospital_encounter.json`, `ViewDefinition.icu_encounter.json`, `ViewDefinition.condition.json`, and `concept.sql` in `mimic-iv/concepts_fhir/concepts/score/apsiii/attempt_0001/`.
