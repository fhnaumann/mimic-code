# Demo shape-gate evidence

- Command: `uv run mimic_utils run-demo rhythm`.
- Concept/attempt: `rhythm`, `0003`.
- Outcome: `shape_ok`, exit code 0; embedded Pathling on Spark executed successfully and registered `rhythm_encounter`, `rhythm_observation`, and `rhythm_patient`.
- Candidate columns: `subject_id`, `patient_key`, `charttime`, `heart_rhythm`, `ectopy_type`, `ectopy_frequency`, `ectopy_type_secondary`, `ectopy_frequency_secondary`. The extra `patient_key` is the manifest-declared required key column; no expected column is missing.
- Types were compatible: integer subject id, timestamp charttime, and five strings.
- Demo returned 12,437 rows. This is reported only and was not gated.
- Artifacts: `candidate.demo.parquet/` and `shape.demo.json` in the attempt directory. No errors; no authored artifact or state change was made by the runner.
