# Source analyst evidence — enzyme attempt 0003

This analysis stage was reused from the valid carryover at
`mimic-iv/concepts_fhir/carryover/enzyme/source-analyst.md` rather than spawned
again. It establishes that `enzyme.sql` reads only `mimiciv_hosp.labevents`,
filters the eleven exact itemids to positive non-NULL `valuenum`, groups by
`specimen_id`, and independently computes the MAX pivots and output fields.
The DAG has no dependencies; the manifest key is `specimen_id`.
