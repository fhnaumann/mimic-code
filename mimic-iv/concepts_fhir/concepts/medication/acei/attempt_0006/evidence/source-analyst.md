# Source analyst evidence — acei attempt 0006

This analysis stage was reused from the valid carryover at
`mimic-iv/concepts_fhir/carryover/acei/source-analyst.md` rather than respawned.
That carryover identifies `mimiciv_hosp.prescriptions` as the only source table,
the ten case-insensitive ACEI substring filters, the direct row-preserving
semantics, nullable prescription timestamps, no dependencies, and the
unkeyed full-tuple output shape. Its recorded DAG SHA256 matches the current
source SQL.

No new source analysis was performed for this retry, and no source-stage note
was appended.
