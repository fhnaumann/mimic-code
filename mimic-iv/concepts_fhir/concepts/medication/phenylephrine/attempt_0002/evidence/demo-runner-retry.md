# Demo runner retry evidence

- Concept: `phenylephrine`; attempt: `0002`.
- The initial demo invocation was blocked by local Spark networking. Retrying with `SPARK_LOCAL_IP=127.0.0.1 SPARK_DRIVER_HOST=127.0.0.1` allowed the embedded Spark/Pathling execution to complete.
- Result: 625 rows (informational only), six expected columns, compatible types, and `SHAPE OK`.
- Artifacts produced: `candidate.demo.parquet` and `shape.demo.json` in this attempt directory.
- The successful demo is only permission to spend a full-data run; it is not correctness evidence.
