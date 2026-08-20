Evidence block

FHIR mapping reused from carryover (no new subagent run):
`mimic-iv/concepts_fhir/carryover/crrt/fhir-prober.md`.

The CRRT source maps to chartevents-derived `Observation` resources filtered by
the exact MIMIC chartevents CodeSystem and item codes, joined to ICU
`Encounter` by reference/resource key equality and ICU identifier system.
Quantity and string value variants, repeated item 224146 rows, and the known
chartevents DST normalization were checked in the carryover probe. Resource ids
were treated as opaque identity and not used for semantic recovery.
