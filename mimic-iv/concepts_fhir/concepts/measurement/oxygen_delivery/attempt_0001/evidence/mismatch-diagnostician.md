## Evidence

Diagnosed the executed full-data review using `comparison.full.json`, the
attempt's ViewDefinitions and `concept.sql`, canonical source SQL, carryover,
`MIMIC_NOTES.md`, and upstream `mimic-fhir/sql/fhir_observation_chartevents.sql`.

The divergence is intrinsic upstream timestamp transformation, not a port bug:
31 candidate-only rows pair with 31 oracle-only rows through the comparator's
full DST key replay; three collision rows remain oracle-only and three matched
rows conflict on flow/device pivots. Upstream
`mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` casts `charttime` through
`TIMESTAMPTZ` before writing `Observation.effectiveDateTime`, normalizing
nonexistent New York spring-forward 02:xx wall times to 03:xx. The original
temporal grouping is unrecoverable by a compliant FHIR query; `issued` is
storetime and resource IDs are opaque.

The loss is essential for this concept: charttime is the semantic grain and
controls row inclusion, ranking, joining, grouping, and clinical flow/device
outputs. No carryover invalidation or implementation fix is indicated. The
independent judge must decide, with a recommendation to block rather than
accept an ordinary ancillary divergence.

No new notes fragment entry was needed; the curated notes already record this
dataset-wide DST transformation.
