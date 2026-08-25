# Demo shape gate evidence

- Concept: `first_day_lab`, attempt `0003`.
- Command: `uv run mimic_utils run-demo first_day_lab --attempt 3`.
- Engine: embedded Pathling on Spark over the demo Delta warehouse.
- Result: `shape_ok`; execution succeeded, all expected columns were present,
  and `incompatible_types` was empty. The two additional columns,
  `icu_encounter_key` and `patient_key`, are the manifest-declared required
  resource key columns. Candidate row count was 140 and was not used as a gate.
- Read: `shape.demo.json` and the oracle manifest.
- Replay integrity: `concept.sql`, both ViewDefinitions, and
  `replay_provenance.json` in this attempt were copied byte-identically from
  the already-created replay artifacts; no implementation artifact was
  re-authored.
- Artifacts: `candidate.demo.parquet/` and `shape.demo.json`.
