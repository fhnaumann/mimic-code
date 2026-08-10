# Demo runner evidence

Attempt 0001 was frozen in `VALIDATING_DEMO`. `uv run mimic_utils run-demo arb` executed successfully with embedded Pathling on Spark over `/Users/nau025/warehouses/mimic-iv-demo/delta`; no HTTP server was used.

Shape verdict: `shape_ok`. Returned columns `[subject_id, hadm_id, arb, starttime, stoptime]` exactly match the manifest. Types were compatible: `int`, `int`, `string`, `timestamp_ntz`, `timestamp_ntz` versus `INTEGER`, `INTEGER`, `VARCHAR`, `TIMESTAMP`, `TIMESTAMP`. Demo returned 35 rows; row count is explicitly non-gating under the contract. The concept is unkeyed and uses full-tuple multiset comparison.

Artifacts: `candidate.demo.parquet/` and `shape.demo.json` under `mimic-iv/concepts_fhir/concepts/medication/arb/attempt_0001/`. No implementation or shared-note files were changed.
