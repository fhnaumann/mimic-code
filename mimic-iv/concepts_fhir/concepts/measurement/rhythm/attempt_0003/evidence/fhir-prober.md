# FHIR prober carryover evidence

`fhir-prober` was reused for attempt `0003` from
`mimic-iv/concepts_fhir/carryover/rhythm/fhir-prober.md`, recorded by the
controller as reusable. The carryover maps the five codes to the
`mimic-chartevents-d-items` Observation coding system, categorical values to
`valueString`, identifiers through Patient/ICU Encounter equality joins, and
effective time through `effective.ofType(dateTime)` with `TIMESTAMP_NTZ`.
Resource keys remain opaque. No new FHIR probe was run in this attempt.
