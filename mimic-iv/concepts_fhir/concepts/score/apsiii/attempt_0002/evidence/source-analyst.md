# Source-analyst evidence (reused carryover)

The existing `apsiii` carryover analysis was reused for attempt 0002 under the
resume plan. It reads the canonical `mimic-iv/concepts/score/apsiii.sql`, DAG
metadata, manifest, and dependency SQL definitions, and records the one-row
per-`stay_id` grain, all joins/filters/windows, exact scoring CASE logic,
dependency boundaries, output schema, null behavior, and essential inputs.

Reusable artifact: `mimic-iv/concepts_fhir/carryover/apsiii/source-analyst.md`.
No new source analysis was spawned and no implementation artifact was authored
by this stage.
