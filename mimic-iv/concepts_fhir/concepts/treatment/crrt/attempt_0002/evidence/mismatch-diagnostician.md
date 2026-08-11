## Evidence

Attempt 0002 remains a fixable semantic bug; no judge is convened. The UUID
namespace, value reconstruction, FHIR mappings, filters, join, and repeated
item pivot are correct. The remaining error is `DATE_FORMAT` at
`concept.sql:73-80`: Spark reinterprets a one-hour-subtracted
`TIMESTAMP_NTZ` inside the session-zone DST gap and formats October 02:xx
back as 03:xx. Thus the UUID witness still fails for the October residual.

The independent Spark 4.0.2 check showed NTZ subtraction produces
`2140-10-02 02:00:00`, but `DATE_FORMAT` emits 03:00 while `CAST(... AS
STRING)` preserves 02:00. Replace both UUID-name timestamp renderings with
`CAST(timestamp AS STRING)` in a new attempt; retain the existing UUID
comparison and pivot.

Full-data evidence: all 37 `only_oracle` rows are October 02:xx with a
candidate +1-hour key, all 6 `only_candidate` rows are October 03:xx, and all
27 conflicts are the expected collisions. Upstream
`mimic-fhir/sql/fhir_observation_chartevents.sql:9,21,41,45,67` preserves the
pre-normalization charttime in Observation.id, so recovery is possible and
this is not intrinsic ETL loss. No carryover stage is invalidated. The
dataset-wide Spark formatting finding was appended to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/crrt.md`.
