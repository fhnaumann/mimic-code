# Reused source analysis evidence

Concept `kdigo_stages`, attempt `0002`. The source analysis was reused from
the valid carryover at
`mimic-iv/concepts_fhir/carryover/kdigo_stages/source-analyst.md`, recorded
after attempt 0001. It identifies the canonical source
`mimic-iv/concepts/organfailure/kdigo_stages.sql`, dependencies `crrt`,
`kdigo_creatinine`, and `kdigo_uo`, and the required ICU encounter spine,
stage branches, event-axis union, joins, and six-hour smoothing semantics.
No source analysis was rerun because the retry changes only the completed
dependency version, not this concept's source SQL.

Artifact reused: `mimic-iv/concepts_fhir/carryover/kdigo_stages/source-analyst.md`.
