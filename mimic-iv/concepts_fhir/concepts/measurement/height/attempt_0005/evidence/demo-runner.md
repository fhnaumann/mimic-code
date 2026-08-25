# Demo shape gate evidence — height attempt_0005

Ran `uv run mimic_utils run-demo height` using embedded Pathling on Spark over the demo Delta warehouse. The run executed successfully and produced `shape.demo.json` with verdict `shape_ok`.

The manifest columns all matched: `subject_id` INTEGER, `stay_id` INTEGER, `charttime` TIMESTAMP, and `height` DECIMAL(38,2). No columns were missing and no incompatible types were reported. The candidate also contains additive `patient_key` and `icu_encounter_key` columns; the comparison projects manifest columns explicitly, so these do not affect the shape gate. Demo row count was 69 and was recorded only as a non-gating observation.

Artifacts: `candidate.demo.parquet/` and `shape.demo.json` in this attempt directory. Implementation artifacts were not edited.
