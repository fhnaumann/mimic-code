# Demo shape-gate evidence

- Concept: `icp`
- Attempt: `0005` (replay; implementation artifacts were not edited)
- Command: `uv run mimic_utils run-demo icp`
- Execution: succeeded with exit code 0 using embedded Pathling on Spark; views `icp_icu_encounter`, `icp_observation`, and `icp_patient` registered successfully.
- Verdict: `shape_ok`; proceed to full data. This is not a correctness result.
- Oracle columns: `subject_id INTEGER`, `stay_id INTEGER`, `charttime TIMESTAMP`, `icp FLOAT`.
- Candidate columns: all four oracle columns with compatible types, plus required manifest key columns `patient_key` and `icu_encounter_key`.
- Informational row count: 303 demo rows; row count is not gated.
- Artifacts: `candidate.demo.parquet`, `shape.demo.json`.
