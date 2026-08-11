## Evidence

`uv run mimic_utils run-demo icp` executed attempt_0002 via embedded Pathling on Spark and returned `shape_ok`. The candidate Parquet has exact columns `[subject_id, stay_id, charttime, icp]`, compatible types (`int`, `int`, `timestamp_ntz`, `float`), no missing/extra columns, and the manifest key is present. The 303 demo rows versus 173273 full-oracle rows were reported only and not gated.

Artifacts: `mimic-iv/concepts_fhir/concepts/measurement/icp/attempt_0002/candidate.demo.parquet/` and `shape.demo.json`.
