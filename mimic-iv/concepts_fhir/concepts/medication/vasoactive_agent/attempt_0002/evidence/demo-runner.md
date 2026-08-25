## Evidence block

**Concept:** vasoactive_agent  
**Attempt:** attempt_0002  
**Verdict:** `shape_fail`

`uv run mimic_utils run-demo vasoactive_agent` failed before producing output. The
replayed `concept.sql` references `m.stay_id` in the `milrinone_rows` CTE
(line 64), but the current `milrinone` dependency view exposes no `stay_id`.
The error was an unresolved-column Spark analysis failure; columns and types
were therefore not comparable and no row count was produced. No implementation
artifact was edited; the CLI produced no `candidate.demo.parquet` or
`shape.demo.json`.

Artifacts read: the replayed `concept.sql`, both ViewDefinitions, and the oracle
manifest. This evidence records the demo-runner result for the replay attempt.
