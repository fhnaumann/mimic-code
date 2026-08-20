# FHIR-probe carryover — norepinephrine attempt_0003

The valid FHIR mapping was reused rather than respawned. ICU
MedicationAdministration is filtered by the exact `mimic-medication-icu` /
`221906` coding; ICU Encounter identifiers recover `stay_id`; both effective[x]
variants and Quantity fields are projected; opaque patient and ICU encounter
keys are retained; and missing `linkorderid` is declared as a typed NULL.

Reusable evidence: `mimic-iv/concepts_fhir/carryover/norepinephrine/fhir-prober.md`.
