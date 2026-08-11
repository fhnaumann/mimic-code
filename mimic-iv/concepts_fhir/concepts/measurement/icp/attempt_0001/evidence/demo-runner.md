## Evidence

The demo runner attempted `uv run mimic_utils run-demo icp` after the controller entered `VALIDATING_DEMO`. The immutable attempt already contained the candidate Parquet and `shape.demo.json` from the implementer's embedded Spark execution, so the write-once guard correctly refused a second execution without editing artifacts. The authoritative shape result is `shape_ok`: execution succeeded via embedded Pathling on Spark, columns exactly match `[subject_id, stay_id, charttime, icp]`, and types are compatible with the oracle manifest. The 303 demo rows versus the full oracle's 173273 rows were reported only and not gated.

Artifacts: `mimic-iv/concepts_fhir/concepts/measurement/icp/attempt_0001/shape.demo.json` and `candidate.demo.parquet/`. No artifacts were modified and no commit was made.
