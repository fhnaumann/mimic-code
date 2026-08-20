# Source-analysis carryover — norepinephrine attempt_0003

The valid source analysis was reused rather than respawned. The canonical
query scans `mimiciv_icu.inputevents` for exact `itemid = 221906`, with no
joins, aggregates, or dependencies, and emits six columns including the
patientweight-sensitive `vaso_rate` CASE.

Reusable evidence: `mimic-iv/concepts_fhir/carryover/norepinephrine/source-analyst.md`.
