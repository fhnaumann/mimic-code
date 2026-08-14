# Evidence: source-analyst (reused carryover)

The reusable source analysis was read from `mimic-iv/concepts_fhir/carryover/oxygen_delivery/source-analyst.md`. It identifies `mimiciv_icu.chartevents` as the sole source, exact itemids `223834`, `227582`, `227287`, and `226732`, the flow/device windows and ranking, the flow-driven join, and the final `(subject_id, charttime)` grain. It also flags charttime DST normalization as potentially aggregation-sensitive. No new source analysis was spawned because carryover was valid.
