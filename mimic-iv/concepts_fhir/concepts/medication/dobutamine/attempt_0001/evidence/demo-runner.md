# Demo-runner evidence

Ran `uv run mimic_utils run-demo dobutamine` with embedded Pathling 9.6.0 on Spark over `/Users/nau025/warehouses/mimic-iv-demo/delta`. Both ViewDefinitions registered and SQL executed successfully. Returned column names exactly matched the manifest: `stay_id`, `linkorderid`, `vaso_rate`, `vaso_amount`, `starttime`, `endtime`; types were compatible (`int,int,float,float,timestamp_ntz,timestamp_ntz`). The observed 44 demo rows were explicitly not gated; full oracle size is 8,513. Shape verdict: `shape_ok`, proceed to full data.

Artifacts produced: `mimic-iv/concepts_fhir/concepts/medication/dobutamine/attempt_0001/candidate.demo.parquet` and `shape.demo.json`.
