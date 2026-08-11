# Mismatch diagnostician evidence — `gcs`

- Concept: `gcs`; attempt: `0002`.
- Read/checked: `comparison.full.json`, `run_meta.full.json`, all attempt-0002 ViewDefinitions and `concept.sql`, canonical `mimic-iv/concepts/measurement/gcs.sql`, carryover analyses, `MIMIC_NOTES.md`, all notes fragments, and upstream `mimic-fhir/sql/fhir_observation_chartevents.sql` plus `fhir_etl/uuid_namespace.sql`.
- Result: fixable semantic port bug, not intrinsic ETL loss. The SQL pivots on DST-normalized `Observation.effectiveDateTime`; it must use the Observation UUID witness (built from original source charttime and value) to recover a one-hour-earlier source charttime before pivoting. Carryover stages remain valid; no invalidation is required.
- Full-data confirmation: all `98` `only_oracle` keys pair to a candidate key exactly one hour later; all `74` `only_candidate` keys pair one hour earlier; non-key values agree. `24` shifted rows collide with genuine 03:xx rows, explaining the row deficit. All occur on March DST spring-forward Sundays. The upstream normalization is `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`; UUID construction preserving original time/value is at `:21,41,45`, with namespace in `fhir_etl/uuid_namespace.sql:27`.
- Action: semantic rework is required; create a new immutable attempt with corrected SQL. No existing artifact was edited and no commit was made.
