# Demo-runner evidence — bg retry

**Attempt:** `measurement/bg/attempt_0002`; verdict `shape_ok`.

Embedded Pathling on Spark registered the five ViewDefinitions and executed
`concept.sql` successfully. All 27 expected columns were present with no
extras. Spark types (`int`, `timestamp_ntz`, `string`, `double`, `float`, and
`decimal(38,4)`) were compatible with the manifest; in particular,
`fio2_chartevents` is FLOAT and `aado2_calc` is DECIMAL(38,4).

The demo produced 889 rows. This count is informational only; row count is not
a demo gate. The attempt may proceed to full-data validation.

**Artifacts:**

- `candidate.demo.parquet`
- `shape.demo.json`
