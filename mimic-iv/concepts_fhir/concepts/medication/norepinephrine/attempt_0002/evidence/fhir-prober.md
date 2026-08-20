# FHIR-probe carryover — norepinephrine attempt_0002

The FHIR-prober stage was reused from the recorded carryover for this concept,
rather than respawned. The mapping uses ICU
`MedicationAdministration` with exact coding system/code
`mimic-medication-icu`/`221906`, an ICU Encounter identifier to recover
`stay_id`, MedicationAdministration subject/context reference keys for opaque
identity joins, both effective[x] variants, and Quantity rate/dose values.
`linkorderid` and `patientweight` have no served FHIR element; the former is
declared unrepresentable and emitted as typed NULL.

Reusable probe evidence: `mimic-iv/concepts_fhir/carryover/norepinephrine/fhir-prober.md`.
