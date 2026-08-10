Evidence block — chemistry attempt_0003

`uv run mimic_utils run-demo chemistry` executed cleanly with embedded Pathling on Spark 9.6.0 against the local demo Delta warehouse. ViewDefinitions registered: `encounter`, `lab_observation`, `patient`, `specimen`.

Verdict: `shape_ok`. Candidate columns exactly matched the oracle manifest with no extra or missing columns. `subject_id`, `hadm_id`, and `specimen_id` were INTEGER; `charttime` was TIMESTAMP/TIMESTAMP_NTZ-compatible; all analytes were DOUBLE; `incompatible_types: []`. Demo row count was 3,289 and was treated as a non-gating observation.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/measurement/chemistry/attempt_0003/candidate.demo.parquet`
- `mimic-iv/concepts_fhir/concepts/measurement/chemistry/attempt_0003/shape.demo.json` (`verdict: shape_ok`, `executed: true`)

No state transitions, implementation changes, or notes were made by the runner.
