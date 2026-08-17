# Demo evidence — `bg`, attempt 0007

`uv run mimic_utils run-demo bg` executed successfully through the embedded
Pathling/Spark path. The shape verdict was `shape_ok` with execution success,
all 27 manifest column names present, no unexpected compared columns, and no
incompatible types. The extra `patient_key` and `encounter_key` columns are the
manifest-declared required resource key columns, not a shape failure.

The Parquet schema matched the expected types, including `TIMESTAMP_NTZ` for
`charttime`, `FLOAT` for `fio2_chartevents`, and `DECIMAL(38,4)` for
`aado2_calc`. Demo output had 889 rows; this count was observed only and was not
used as a gate. The demo passed permission to spend an HPC full-data run.

Artifacts:

- `candidate.demo.parquet`
- `shape.demo.json`
