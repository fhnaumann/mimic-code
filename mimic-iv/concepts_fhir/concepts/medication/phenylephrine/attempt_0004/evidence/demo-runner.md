# Demo runner evidence

Concept: phenylephrine  
Attempt: 0004 (replay/data rebuild)

`uv run mimic_utils run-demo phenylephrine` completed successfully with embedded Pathling on Spark over the demo Delta warehouse. The candidate executed, registered `encounter_icu` and `medication_administration`, and produced the expected six oracle columns plus the two manifest key columns (`patient_key`, `icu_encounter_key`). No columns were missing or unexpected after key-column handling, and all types were compatible. The shape verdict is `shape_ok` / pass. The observed demo row count was 625; row count was reported only and was not gated. No errors occurred.

Artifacts: `candidate.demo.parquet/` and `shape.demo.json` in this attempt directory. The replay-carried `concept.sql`, ViewDefinitions, `unrepresentable.json`, and `replay_provenance.json` were not edited.
