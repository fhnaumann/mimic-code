# Concept implementer evidence

Concept: `icustay_times`; attempt: `0001`.

Created four ViewDefinitions for Patient, ICU Encounter, hospital Encounter,
and heart-rate Observation, plus `concept.sql`. The SQL preserves the ICU
Encounter backbone with LEFT JOINs, filters Observation coding by the exact
chartevents system and code `220045`, casts identifier strings to INTEGER, and
casts FHIR datetime strings to `TIMESTAMP_NTZ`. It conditionally tests the
served Observation UUID witness to recover a source DST-gap charttime, while
leaving genuine 03:xx observations unchanged. No unrepresentable columns were
identified and no notes fragment was modified.

Checks performed: ViewDefinition labels and JSON structure were checked, and
`uv run mimic_utils lint-sql icustay_times` passed. Artifacts:
`mimic-iv/concepts_fhir/concepts/demographics/icustay_times/attempt_0001/`.
