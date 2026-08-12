# Mismatch diagnostician evidence

The judge's `bug` finding was caused by incorrect comparator attribution
metadata, not by the port. The candidate sources `charttime` from
`Observation.effectiveDateTime` (`ViewDefinition.lab_observation.json:14`,
`concept.sql:26`). The relevant upstream ETL is
`mimic-fhir/sql/fhir_observation_labevents.sql:15,121`, which casts
`labevents.charttime` through `TIMESTAMPTZ` and writes the result to
`Observation.effectiveDateTime`. The comparison's citations to
`fhir_encounter.sql:65` and `fhir_medication_request.sql:43-44` write unrelated
FHIR elements and fail the judge's provenance check.

The sole conflict, oracle `2150-03-08 02:07` versus FHIR `03:07`, is fully
replayed as the America/New_York DST-gap transformation and is unrecoverable;
117,897/117,898 rows otherwise match. No carryover stage is implicated and no
implementation retry is warranted. The unchanged review should be rejudged
with the corrected ETL citation.
