# FHIR prober evidence

The prober read the source carryover, curated notes, relevant provisional
fragments, the completed `vasoactive_agent` attempt, the manifest, and the
ICU MedicationAdministration ETL, then probed the authoritative Delta with
embedded Pathling 9.6.0 on Spark 4.0.2.

The candidate must consume the completed dependency as `FROM vasoactive_agent`;
it must not rederive the interval overlay from raw FHIR resources. The
dependency supplies `stay_id`, `starttime`, `endtime`, the five target rate
columns, and required opaque support keys. The target manifest is an unkeyed
full-tuple multiset with ordinary columns `stay_id`, `starttime`, `endtime`,
and `norepinephrine_equivalent_dose`, plus required opaque
`icu_encounter_key`/`patient_key` support columns.

The transitive ICU MedicationAdministration codes were confirmed under
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu`: dobutamine
221653 (44), dopamine 221662 (28), epinephrine 221289 (36), norepinephrine
221906 (947), phenylephrine 221749 (625), vasopressin 222315 (55), and
milrinone 221986 (15), each one coding per resource, 1,750/1,750 total. The
dependency's target keeps only its five named rate columns; dobutamine and
milrinone affect upstream boundaries but are not summands.

Relevant paths are `context.getReferenceKey(Encounter)`, ICU Encounter
`identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value`,
`subject.getReferenceKey(Patient)`, both `effective` dateTime/Period variants,
and both dosage Quantity value/unit variants. Quantity aliases are strings and
raw values are decimal(32,6); datetime strings require `TIMESTAMP_NTZ` casts.
The demo had 1,874 dependency rows, 1,748 retained by the source disjunction,
and two duplicate interval coordinates, so no deduplication is allowed.

Patientweight and inputevent linkorderid are absent from served
MedicationAdministration. Patientweight-dependent target branches were not
exercised in the demo, so any full-data rate-unit branch must be handled as a
typed NULL in the dependency rather than estimated or recovered from an
opaque id. ICU effective times may also carry the established DST-gap
transformation loss. These are evidence for later full-data adjudication, not
an early terminal decision.

The prober wrote and recorded reusable analysis at
`mimic-iv/concepts_fhir/carryover/norepinephrine_equivalent_dose/fhir-prober.md`
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/norepinephrine_equivalent_dose.md`:
`MedicationAdministration.context` is the encounter link, one coding is
served per medication administration, CodeSystem resources are absent,
patientweight is not serialized, and ICU Quantity unit strings are trimmed.
`MIMIC_NOTES.md` was not modified.
