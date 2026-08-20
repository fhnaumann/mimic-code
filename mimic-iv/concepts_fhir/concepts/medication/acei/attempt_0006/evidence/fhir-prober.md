# FHIR prober evidence — acei attempt 0006

This mapping stage was reused from the valid carryover at
`mimic-iv/concepts_fhir/carryover/acei/fhir-prober.md` rather than respawned.
That carryover maps pharmacy-backed hospital prescriptions to
`MedicationRequest`, resolves direct `Medication` name identifiers and
medication-mix ingredient references, preserves multiplicity with `UNION ALL`,
joins Patient and hospital Encounter by opaque resource-key equality, and
uses validity-period endpoints with `TIMESTAMP_NTZ` parsing. It also records
the relevant missing-validity and DST transformation evidence and the exact
ten ACEI filters.

The reopened implementation instruction was additive: this attempt retains
the five oracle columns and emits the required paired resource-key support
columns. No new probe was performed and no dataset-wide notes fragment was
appended by this reused stage.
