# Demo runner evidence

Concept: `apsiii`, attempt `0001`.

Executed `uv run mimic_utils run-demo apsiii` with embedded Pathling 9.6.0 on Spark over `/Users/nau025/warehouses/mimic-iv-demo/delta`. The ViewDefinitions and `concept.sql` executed successfully with 21 dependency views registered. The shape verdict was `shape_ok`: all 21 manifest columns were present with compatible types, `apsiii_prob` was `DOUBLE`, the other manifest outputs were `INTEGER`, and the three sanctioned FHIR key columns were present as `VARCHAR`. The demo produced 140 rows; this count was reported only and was not gated.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` under `mimic-iv/concepts_fhir/concepts/score/apsiii/attempt_0001/`. The pass only permits the full-data run; it is not a correctness result.
