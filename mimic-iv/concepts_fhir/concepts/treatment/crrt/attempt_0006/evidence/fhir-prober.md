# FHIR prober evidence

Reused carryover mapping for `crrt` (attempt 1). Targeted ICU chartevent Observations are selected by the exact MIMIC chartevents coding system and item code, joined to ICU Encounter identifiers by opaque reference/resource-key equality, with numeric Quantity aliases cast in outer SQL. Repeated observations, polymorphic values, and the known datetime normalization were considered; resource-id inversion is forbidden and was removed.

Carryover artifact: `mimic-iv/concepts_fhir/carryover/crrt/fhir-prober.md`.
