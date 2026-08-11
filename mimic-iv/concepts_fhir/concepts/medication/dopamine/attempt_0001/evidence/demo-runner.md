Evidence block — Concept: dopamine, attempt 0001.

`uv run mimic_utils run-demo dopamine` completed successfully using embedded Pathling on Spark over the local demo Delta warehouse. The registered views were `encounter_icu` and `medication_administration`. The candidate schema was `stay_id int`, `linkorderid int`, `vaso_rate float`, `vaso_amount float`, `starttime timestamp_ntz`, and `endtime timestamp_ntz`; all six names matched the manifest and all types were compatible. The shape verdict was `shape_ok`. The candidate had 28 demo rows; row count was observed only and was not gated.

Artifacts produced: `candidate.demo.parquet` and `shape.demo.json` in `mimic-iv/concepts_fhir/concepts/medication/dopamine/attempt_0001/`.
