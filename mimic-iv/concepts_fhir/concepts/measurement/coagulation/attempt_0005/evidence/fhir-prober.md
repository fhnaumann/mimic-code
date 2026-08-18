# FHIR prober evidence — coagulation attempt 0005

The FHIR-probing stage was reused from the recorded carryover because the
concept mapping facts were unchanged. Read:
`mimic-iv/concepts_fhir/carryover/coagulation/fhir-prober.md`.

The mapping uses labevents-derived `Observation` resources filtered by the
exact `mimic-d-labitems` system and six string codes, joins patient and lab
specimen identifiers through opaque resource keys, left-joins hospital
Encounter for nullable `hadm_id`, extracts Quantity values while excluding
comparator-bearing/text rows, and casts FHIR datetimes to `TIMESTAMP_NTZ`.
Specimen identifier grouping preserves the source grain. The carryover also
records the known lab DST-gap transformation and the required paired resource
key outputs. No new dataset-wide finding was established in attempt 0005.

Carryover probe evidence remains at:
`mimic-iv/concepts_fhir/carryover/coagulation/fhir-prober.md`.
