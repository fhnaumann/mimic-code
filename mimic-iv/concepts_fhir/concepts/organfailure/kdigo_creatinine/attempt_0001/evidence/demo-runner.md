# Demo-runner evidence

The frozen attempt's embedded Pathling/Spark demo run completed with `shape_ok`. The recorded `shape.demo.json` and Parquet schema have the exact six oracle columns and compatible types: `hadm_id INTEGER`, `stay_id INTEGER`, `charttime TIMESTAMP`, and the three creatinine value columns as `DOUBLE`. The candidate demo row count was 1,272; this was informational and not gated. A second invocation correctly refused because the Parquet artifact is write-once.

Artifact: `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_creatinine/attempt_0001/shape.demo.json` and `candidate.demo.parquet`.
