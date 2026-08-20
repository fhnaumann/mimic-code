# Demo-runner evidence

- Concept: `dopamine`; attempt: `0003`; command: `uv run mimic_utils run-demo dopamine`.
- Embedded Pathling on Spark executed both ViewDefinitions and `concept.sql`
  successfully and wrote `candidate.demo.parquet`.
- Shape verdict: `shape_ok`; all six oracle column names and compatible types
  matched. Required extra manifest key columns `patient_key` and
  `icu_encounter_key` were present; no unexpected columns were reported.
- Observed demo row count: 28. This was not used as a gate.
- Artifacts: `candidate.demo.parquet` and `shape.demo.json` in this attempt.
- No implementation, state, notes, sibling, or prior-attempt files were
  modified.
