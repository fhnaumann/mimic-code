## Full-data mismatch-diagnostician evidence

The attempt-2 full verdict is `review`, tier `contested`: 18 `differing_conflict` rows, all `charttime`, with candidate values exactly one hour ahead on DST spring-forward timestamps. Schema and row counts match; 295,228/295,246 rows are identical, with no only-oracle, only-candidate, or null-only classes.

This is irrecoverable upstream transformation loss, not a port bug. `mimic-fhir/sql/fhir_observation_labevents.sql:15` casts naive `lab.charttime` through `TIMESTAMPTZ`, and line 121 writes the transformed value to `Observation.effectiveDateTime`. Nonexistent spring-forward `02:xx` wall times become `03:xx`; the operation is non-injective, and FHIR retains no original wall-clock value. The alternate `Specimen.collection.collectedDateTime` is transformed identically at `mimic-fhir/sql/fhir_specimen_lab.sql:9,18,58`; `Observation.issued` is based on `storetime`, not charttime. Therefore no FHIR query can recover the oracle timestamp without corrupting genuine 03:xx values.

The source SQL and implementation both correctly apply MAX(charttime) per specimen. No carryover stage is implicated, there are no dependencies, and no new notes-fragment entry was needed because the curated DST-gap quirk already covers this transformation. Recommendation: no retry; convene the equivalence judge with the cited ETL statements.
