# Demo shape gate evidence

- Concept: `first_day_urine_output`
- Attempt: `0002` replayed data-rebuild attempt; carried SQL and ViewDefinitions were not edited.
- Result: `shape_ok`; embedded Pathling on Spark executed successfully and the gate permitted full-data validation.
- Expected columns/types: `subject_id` INTEGER, `stay_id` INTEGER, `urineoutput` DOUBLE.
- Returned columns/types: `subject_id` int, `stay_id` int, `urineoutput` double; declared `patient_key` and `icu_encounter_key` were also present.
- Shape details: no missing columns and no incompatible types. Demo row count was 140 and was not used as a gate; the full oracle count is 73,181.
- The later rerun refusal was only the write-once guard for the existing `candidate.demo.parquet`, not a shape failure.
- Artifact: `shape.demo.json`.
