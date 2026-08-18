Evidence block

- Concept: `oxygen_delivery` — attempt `0003`.
- Verdict: `shape_ok` (SHAPE OK).
- Embedded Spark execution succeeded: Spark lease acquired, three ViewDefinitions registered (`oxygen_delivery_encounter`, `oxygen_delivery_observation`, `oxygen_delivery_patient`), and no execution error occurred. A subsequent invocation was refused only by the write-once guard because `candidate.demo.parquet` already existed.
- All nine oracle-manifest columns are present with compatible types; no missing or incompatible columns. The declared extra `patient_key` and `icu_encounter_key` columns are the required manifest key columns.
- Candidate demo row count was 1,154; row count is observational and not gated.
- Artifacts: `candidate.demo.parquet` and `shape.demo.json` under `mimic-iv/concepts_fhir/concepts/measurement/oxygen_delivery/attempt_0003/`.
- Gate outcome: may proceed to full data.
