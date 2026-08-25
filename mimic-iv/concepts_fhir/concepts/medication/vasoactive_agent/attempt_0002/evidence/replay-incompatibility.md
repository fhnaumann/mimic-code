## Replay incompatibility diagnosis

The replayed attempt cannot reach the demo gate because its byte-identical SQL
expects `milrinone.stay_id` in the dependency view. In the earlier dependency
published shape used by vasoactive_agent attempt_0001, milrinone exposed
`stay_id`. The completed current `milrinone` attempt_0003 also computes
`stay_id`, but it additionally publishes `icu_encounter_key`; the embedded
dependency preprocessor applies `strip_mimic_ids`, which removes `stay_id` when
the paired ICU resource key is present. Consequently the published
`milrinone` temp view has no `stay_id`, and Spark rejects
`vasoactive_agent/attempt_0002/concept.sql:64` before execution.

This is not a served-data measurement: it is an interface incompatibility
between the carried target SQL and the current published dependency shape.
Because this is a `[replay:data_rebuild]` attempt, the carried SQL and
ViewDefinitions must remain byte-identical; silently editing or re-authoring
them would invalidate the replay. The replay therefore cannot proceed without
human-authorized re-authoring of the target for the migrated dependency
interface.

Checked artifacts: the replayed target `concept.sql`, current
`milrinone/attempt_0003/concept.sql` and demo Parquet schema, the dependency
preprocessor (`src/mimic_utils/embedded_runner.py:352-385`), and
`strip_mimic_ids` (`src/mimic_utils/export_mappings.py:273-307`). No
dataset-wide MIMIC/FHIR quirk was found and no shared note was appended.
