# FHIR-prober evidence (reused carryover)

The FHIR mapping was reused from `mimic-iv/concepts_fhir/carryover/kdigo_creatinine/fhir-prober.md`, recorded after attempt 0001. It maps ICU Encounters by the ICU identifier system, hospital admission ids through the ICU Encounter `partOf` reference, and creatinine Observations by the exact labevents coding system/code `50912`, with patient/time joins, numeric Quantity casting, and direct `TIMESTAMP_NTZ` parsing of `effectiveDateTime`. It confirms incomplete lab Observation Encounter references and the established DST-gap transformation. Resource/reference keys remain opaque equality-join values.

Artifact reused: `mimic-iv/concepts_fhir/carryover/kdigo_creatinine/fhir-prober.md`.
