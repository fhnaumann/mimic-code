# Demo-runner evidence

The replayed `first_day_bg` attempt_0003 ran successfully with embedded Pathling on Spark over the demo Delta warehouse. The shape verdict was `shape_ok`; all 44 oracle columns were present with compatible types, and the declared `patient_key` and `icu_encounter_key` columns were present as candidate-side key artifacts. The demo produced 140 rows; row count was observation only and was not gated. No attempt implementation artifacts were edited.

Produced artifacts: `candidate.demo.parquet` and `shape.demo.json` in this attempt directory.
