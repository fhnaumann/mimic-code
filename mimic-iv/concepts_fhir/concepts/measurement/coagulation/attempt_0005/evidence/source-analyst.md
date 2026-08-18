# Source analyst evidence — coagulation attempt 0005

The source-analysis stage was reused from the recorded carryover because the
concept SQL and source facts were unchanged. Read:
`mimic-iv/concepts_fhir/carryover/coagulation/source-analyst.md`.

It establishes that `measurement/coagulation.sql` is a dependency-free pivot
over `mimiciv_hosp.labevents`, filtering the six literal itemids 51196, 51214,
51297, 51237, 51274, and 51275 plus `valuenum IS NOT NULL`, grouping by
`specimen_id`, and independently applying `MAX` to metadata and analyte
values. The target shape is ten oracle columns with `specimen_id` as the
natural key. No new source finding was needed for attempt 0005.

Carryover source evidence remains at:
`mimic-iv/concepts_fhir/carryover/coagulation/source-analyst.md`.
