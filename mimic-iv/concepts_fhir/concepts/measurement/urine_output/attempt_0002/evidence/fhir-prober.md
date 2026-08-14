# FHIR prober evidence

Attempt `0002` reused the validated concept-level FHIR mapping from attempt `0001`; no FHIR warehouse or source mapping changed. The reusable artifact is `mimic-iv/concepts_fhir/carryover/urine_output/fhir-prober.md`, recorded in `carryover.json`. It maps outputevents to Observation, ICU stay through Encounter identifier equality, dateTime effective time to `TIMESTAMP_NTZ`, Quantity value to `DOUBLE`, and exact itemid strings under the `mimic-d-items` system. It also records that outputevents effective timing is dateTime-only and that resource IDs are opaque.

This stage was reused under the carryover protocol; no new probe was needed and no attempt implementation artifact was modified.
