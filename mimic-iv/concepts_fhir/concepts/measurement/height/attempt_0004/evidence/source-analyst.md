# Source-analyst evidence (reused carryover)

The source analysis was reused from
`mimic-iv/concepts_fhir/carryover/height/source-analyst.md` because the
concept SQL and DAG source hash are unchanged. It identifies the two exact
chartevents itemids (`226707` inches and `226730` centimetres), the full outer
join on `subject_id + charttime`, centimetre precedence, strict `(120,230)`
height bounds, and the four-column oracle shape. No dependency is present.

The carryover records DAG hash verification, source columns, filters, join,
transformation, and manifest metadata. No new source-analyst subagent was
spawned for attempt 0004.

Artifact read: `mimic-iv/concepts_fhir/carryover/height/source-analyst.md`.
