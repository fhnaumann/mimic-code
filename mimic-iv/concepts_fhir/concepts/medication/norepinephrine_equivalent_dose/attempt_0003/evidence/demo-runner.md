# Demo-runner evidence

- Concept: `norepinephrine_equivalent_dose`
- Attempt: `0003` (REPLAY/data rebuild; carried artifacts were not edited)
- Execution: embedded Pathling on Spark completed successfully with exit code 0.
- Shape verdict: `shape_ok`.
- Oracle columns: `stay_id`, `starttime`, `endtime`, `norepinephrine_equivalent_dose`.
- Candidate columns matched those plus declared key columns `icu_encounter_key` and `patient_key`; no missing or unexpected columns.
- Types were compatible: integer, timestamp, and `decimal(38,4)`.
- Demo row count: 1,748; non-gating observation.
- Artifacts: `candidate.demo.parquet` and `shape.demo.json` in this attempt.
