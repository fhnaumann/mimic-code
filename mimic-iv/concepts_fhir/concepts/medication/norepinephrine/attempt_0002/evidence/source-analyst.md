# Source-analysis carryover — norepinephrine attempt_0002

The source-analysis stage was reused from the recorded carryover for this
concept, rather than respawned. The canonical query is a single filtered scan
of `mimiciv_icu.inputevents` with `itemid = 221906`, no joins, aggregates, or
dependencies, emitting `stay_id`, `linkorderid`, normalized `vaso_rate`, raw
`vaso_amount`, `starttime`, and `endtime`.

Reusable source evidence: `mimic-iv/concepts_fhir/carryover/norepinephrine/source-analyst.md`.
