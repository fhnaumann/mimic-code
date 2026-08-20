Evidence block

Source analysis reused from carryover (no new subagent run):
`mimic-iv/concepts_fhir/carryover/crrt/source-analyst.md`.

The canonical CRRT SQL reads `mimiciv_icu.chartevents`, filters the 19 named
itemids and non-NULL values, and pivots at `(stay_id, charttime)` with MAX.
The full oracle shape is 287,152 rows keyed by `(stay_id, charttime)`.
