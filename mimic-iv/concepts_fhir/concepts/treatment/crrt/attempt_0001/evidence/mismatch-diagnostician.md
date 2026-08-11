## Evidence

The diagnosis read the full comparison, current ViewDefinitions and SQL,
canonical CRRT SQL, oracle manifest, curated notes, all relevant fragments,
and upstream `mimic-fhir` ETL SQL. The current port is a fixable semantic bug,
not an intrinsic contested transformation.

The 85 `only_oracle` rows are source 02:xx charttime keys whose FHIR effective
times were normalized to 03:xx; 22 `only_candidate` rows are the resulting
03:xx keys; and 53 conflicts are aggregation collisions with genuine 03:xx
rows. The SQL drops the projected Observation resource key and pivots on
normalized effective time, so it cannot distinguish the shifted observation.

Upstream evidence: `mimic-fhir/sql/fhir_observation_chartevents.sql:9` casts
the source charttime through `TIMESTAMPTZ`, and line 67 writes the normalized
time to `Observation.effectiveDateTime`; lines 21, 41, and 45 construct and
write the UUIDv5 resource ID from the pre-normalization charttime (namespace
construction: `sql/fhir_etl/uuid_namespace.sql:27`). The resource ID therefore
provides a recoverable equality witness, so this is not accepted as ETL loss.

Fix in a new immutable attempt: retain `observation_key` through typed rows,
recover the original charttime per affected Observation ID, and pivot on the
corrected time without blanket-shifting all 03:xx rows. Neither carryover
stage is invalidated. The diagnostician appended the dataset-wide finding to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/crrt.md`.
