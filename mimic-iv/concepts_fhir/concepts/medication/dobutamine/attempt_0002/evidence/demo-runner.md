# Demo runner evidence

Concept: `dobutamine`  
Attempt: `0002`  
Verdict: `shape_ok`

`uv run mimic_utils run-demo dobutamine` executed successfully with embedded
Pathling on Spark. Both ViewDefinitions registered and `concept.sql` executed.
Returned columns exactly matched the oracle names and order:
`stay_id`, `linkorderid`, `vaso_rate`, `vaso_amount`, `starttime`, `endtime`.
Types were compatible (INTEGER/int, FLOAT/float, TIMESTAMP/timestamp_ntz),
with no incompatible types. The 44 demo rows versus 8,513 full-oracle rows
was reported only and was not gated.

Artifacts produced:
- `candidate.demo.parquet`
- `shape.demo.json`

No execution errors occurred. Full-data correctness remains to be tested on
HPC.
