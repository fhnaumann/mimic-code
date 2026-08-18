# FHIR prober evidence — enzyme attempt 0003

This mapping stage was reused from the valid carryover at
`mimic-iv/concepts_fhir/carryover/enzyme/fhir-prober.md` rather than spawned
again. It maps the labevents stream to Observation, Specimen, Patient, and
hospital Encounter, confirms exact proprietary lab code strings, Quantity
numeric filtering, specimen grouping, incomplete Encounter references, and
the upstream DST-normalized datetime behavior. The implementation follows the
probed `getReferenceKey()` joins and paired output-key requirement without
parsing resource ids.
