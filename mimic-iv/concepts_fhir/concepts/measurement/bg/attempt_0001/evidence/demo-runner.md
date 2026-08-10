# Demo-runner evidence — bg

**Attempt:** `measurement/bg/attempt_0001`.

The embedded Pathling-on-Spark demo gate failed before producing output. Spark
rejected `concept.sql` at line 224 because `CAST(specimen AS VARCHAR)` uses a
bare `VARCHAR`; this Spark dialect requires an explicit length such as
`VARCHAR(255)`. No candidate Parquet or shape artifact was written, so column
and type comparison did not run. The reported zero rows is execution failure,
not the permitted zero-row `unsure` case. The target schema remains 27 columns:
the identifier/timestamp/text columns plus numeric outputs, with
`fio2_chartevents` FLOAT and `aado2_calc` DECIMAL(38,4).

**Required next step:** diagnose the Spark SQL cast issue and create a new
immutable attempt; do not edit this attempt's hand-authored SQL.
