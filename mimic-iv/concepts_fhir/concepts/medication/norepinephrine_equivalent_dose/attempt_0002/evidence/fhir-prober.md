# FHIR prober evidence

The invalidated mapping was re-probed against the authoritative Delta and the
runner's publication shape. The completed `vasoactive_agent` view publishes
`starttime`, `endtime`, rate columns, `icu_encounter_key`, and `patient_key`;
`stay_id` is stripped when the opaque ICU Encounter key is present.

The corrected direct resource mapping is an ICU Encounter ViewDefinition with
`getResourceKey()` as `encounter_key`,
`subject.getReferenceKey(Patient)` as `patient_key`, and the exact ICU
identifier system's `system`/`value` as `stay_system`/`stay_id_str`. Fresh SQL
must cast `stay_id_str` to `INTEGER` and join
`vasoactive_agent.icu_encounter_key = encounter_icu.encounter_key`.

The probe confirmed 140/140 ICU identifiers and exact DuckDB agreement, with
the dependency join matching 1,874/1,874 rows. It reconfirmed the seven ICU
medication codes and one-coding-per-resource ratios (1,750/1,750 total),
Quantity/timing mappings, and the known patientweight, linkorderid,
rate-null-starttime, precision, and DST limitations. No resource-id inversion
or raw interval rederivation is permitted. No new dataset-wide note was
appended; existing owned fragment sections remain unchanged.

Reusable artifact: `mimic-iv/concepts_fhir/carryover/norepinephrine_equivalent_dose/fhir-prober.md`,
recorded for the new attempt.
