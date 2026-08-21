# Reused FHIR-prober evidence

Concept `kdigo_stages`, attempt `0002`. The FHIR mapping was reused from the
valid carryover at
`mimic-iv/concepts_fhir/carryover/kdigo_stages/fhir-prober.md`, recorded after
attempt 0001. It maps ICU `Encounter`, hospital `Encounter`, and `Patient`
through opaque Pathling resource/reference-key equality, preserves identifier
values as explicitly cast numeric outputs, emits the required key columns, and
uses `Encounter.period.start` as a `TIMESTAMP_NTZ` wall-clock value. It also
confirms that the consumer must use completed dependency views rather than
rederive raw observations.

Artifact reused: `mimic-iv/concepts_fhir/carryover/kdigo_stages/fhir-prober.md`.
