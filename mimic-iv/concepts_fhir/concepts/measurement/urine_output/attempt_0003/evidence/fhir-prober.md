# Evidence: fhir-prober (reused)

`fhir-prober` was reused from the recorded carryover because the served mapping is unchanged. Read:
- `mimic-iv/concepts_fhir/carryover/urine_output/fhir-prober.md`
- `mimic-iv/concepts_fhir/MIMIC_NOTES.md`
- `mimic-iv/concepts_fhir/MIMIC_NOTES.d/urine_output.md`

Result: outputevents are `Observation` resources identified by the proprietary `mimic-d-items` system and exact item codes; ICU stay identity is recovered by opaque encounter-key equality and the ICU Encounter identifier value; dateTime and Quantity.value are populated; duplicate observations must survive until aggregation. The carryover mapping remains valid for attempt 0003.

Artifact reused: `mimic-iv/concepts_fhir/carryover/urine_output/fhir-prober.md`.
