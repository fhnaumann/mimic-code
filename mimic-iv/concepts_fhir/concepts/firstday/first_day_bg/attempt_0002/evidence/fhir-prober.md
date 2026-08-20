# Evidence: fhir-prober reuse (`first_day_bg`, attempt 0002)

The FHIR mapping was reused from the registered carryover at
`mimic-iv/concepts_fhir/carryover/first_day_bg/fhir-prober.md` rather than
re-run. It maps ICU `Encounter` resources selected by the ICU identifier
system, the `Patient` identifier spine, `Encounter.period.start` as
`TIMESTAMP_NTZ`, and the completed dependency output exposed as `bg`.

The reopened implementation keeps resource/reference identifiers opaque and
uses them only for equality joins. It adds `patient_key` and
`icu_encounter_key` to the candidate output as required by the current
resource-key contract; the compared MIMIC columns remain unchanged.

Artifacts read: `carryover/first_day_bg/fhir-prober.md`,
`MIMIC_NOTES.md`, and the concept fragment. No new dataset-wide quirk was
discovered and no fragment entry was appended.
