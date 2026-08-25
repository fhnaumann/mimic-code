# Evidence — demo-runner

Concept `gcs`, attempt `0008`; verdict `shape_ok`.

`uv run mimic_utils run-demo gcs` executed successfully with embedded Pathling 9.6.0/Spark 4.0.2 over the demo Delta warehouse. The three ViewDefinitions registered and `concept.sql` ran. All eight oracle columns were present with compatible types; no columns were missing or incompatible. Required manifest key columns `patient_key` and `icu_encounter_key` were present as extra output columns and were not gating failures. Demo row count was 3,279, reported only and not gated.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` under this attempt. The shape artifact reports execution true, shape match true, and verdict `shape_ok`. The demo pass only permits the full-data run; it is not correctness evidence.
