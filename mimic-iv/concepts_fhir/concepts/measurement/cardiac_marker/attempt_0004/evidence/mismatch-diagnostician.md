# Evidence: mismatch-diagnostician

Concept: `cardiac_marker`; attempt `0004`.

The full comparison is a `review` at tier `contested`: schema and row counts
match, 295,228/295,246 rows are identical, and 18 rows conflict only on
`charttime`, with the candidate exactly one hour later. The diagnosis is
intrinsic upstream transformation loss, not a port bug.

The required ETL citation is `mimic-fhir/sql/fhir_observation_labevents.sql:15`,
which casts source `lab.charttime` through `TIMESTAMPTZ` as `lab_CHARTTIME`, and
line 121 writes that transformed value to `Observation.effectiveDateTime`.
The alternate specimen path similarly transforms the value at
separately transformed `storetime` (`fhir_observation_labevents.sql:16,122`),
not an original charttime witness.

The DST spring-forward conversion is non-injective: a nonexistent source
02:xx and a genuine source 03:xx can serialize identically. Correcting every
03:xx FHIR value would corrupt genuine rows, so no FHIR query can recover the
oracle value exactly. The port faithfully uses the FHIR effective datetime via
`TRY_CAST(... AS TIMESTAMP_NTZ)` and must not retry with an arbitrary one-hour
correction. Neither carryover stage is invalidated. No new dataset-wide quirk
was found and no notes fragment was appended.

Evidence read/checked: loop contract, shared notes and fragments, canonical and
attempt SQL/ViewDefinitions, comparison and run metadata, and upstream ETL
source.
