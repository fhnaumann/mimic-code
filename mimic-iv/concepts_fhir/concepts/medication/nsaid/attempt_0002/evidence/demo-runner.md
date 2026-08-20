# Evidence — demo-runner

Concept `nsaid`, attempt `0002`.

`uv run mimic_utils run-demo nsaid` executed cleanly via embedded Pathling on
Spark. Six ViewDefinitions registered and the run completed with exit code 0.
The shape verdict is `shape_ok`: candidate columns were
`subject_id`, `patient_key`, `hadm_id`, `encounter_key`, `nsaid`, `starttime`,
and `stoptime`; the manifest comparison columns and declared key columns were
all present, with no missing or unexpected columns. Types were compatible,
including `TIMESTAMP_NTZ` for the datetime outputs and string resource keys.

The candidate produced 202 demo rows. Row count is reported only and was not a
gate. No implementation artifacts were edited and no new dataset-wide note was
found.

Artifacts:
- `candidate.demo.parquet`
- `shape.demo.json`
