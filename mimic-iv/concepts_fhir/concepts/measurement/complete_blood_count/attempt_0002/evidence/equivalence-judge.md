# Equivalence-judge evidence — complete_blood_count, attempt_0002

Verdict: `accept` for the `contested` review. The schema and row count are
exact; 3,362,299 of 3,362,503 keyed rows are identical, with 204 conflicts
(0.0061%) confined to `charttime`, always candidate +1 hour.

The contested bar is satisfied by the upstream citations
`mimic-fhir/sql/fhir_observation_labevents.sql:15,121` and
`mimic-fhir/sql/fhir_specimen_lab.sql:9,18,58`. Naive source charttimes in the
DST spring-forward gap are cast through TIMESTAMPTZ and written to FHIR;
source 02:xx and genuine 03:xx therefore collapse to the same FHIR value.
Observation.issued is sourced from storetime, identifiers contain only
labevent_id, and the Specimen representation repeats the loss. No FHIR query
can recover the original, while subtracting an hour would corrupt genuine
03:xx values. No divergent dependencies exist and no retry is warranted.

Acceptance justification:

Accepted contested divergence for complete_blood_count attempt_0002: 204 of 3,362,503 keyed rows (0.0061%) differ only in charttime, always candidate +1 hour; schema and row count are exact and 3,362,299 rows are identical. mimic-fhir/sql/fhir_observation_labevents.sql:15 casts naive labevents.charttime to TIMESTAMPTZ and line 121 writes the normalized value to Observation.effectiveDateTime; mimic-fhir/sql/fhir_specimen_lab.sql:9,18,58 performs the same transformation for Specimen.collection.collectedDateTime. During the DST spring-forward gap, source 02:xx and genuine 03:xx collapse to the same FHIR 03:xx value. Observation.issued is storetime (fhir_observation_labevents.sql:16,122), identifiers carry only labevent_id (:12,62,95-98), and no other mimic-fhir SQL writes labevents.charttime, so no FHIR query can recover which preimage occurred; subtracting an hour would corrupt genuine 03:xx values. Attempt_0002 uses the documented TIMESTAMP_NTZ mapping and there are no divergent dependencies.
