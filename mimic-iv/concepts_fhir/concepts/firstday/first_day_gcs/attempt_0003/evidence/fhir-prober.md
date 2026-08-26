# FHIR prober evidence — `first_day_gcs`, attempt 0003

The fhir-prober read `AGENTS.md`, the source analysis carryover, the full
curated `MIMIC_NOTES.md`, all `MIMIC_NOTES.d/*.md` fragments, the canonical
Observation ViewDefinition, and completed `gcs` attempt_0008 artifacts. It
probed the authoritative demo Delta with embedded Pathling 9.6.0/Spark 4.0.2
and checked against the DuckDB source oracle.

The ICU Encounter mapping is selected by the exact
`http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` identifier system.
`subject.getReferenceKey(Patient)` joins to Patient
`identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value`
for numeric `subject_id`; the ICU identifier `value` supplies numeric
`stay_id`; `period.start` supplies `intime`; and `getResourceKey()` values are
preserved as the opaque `patient_key` and `icu_encounter_key` companions.
The published `gcs` dependency must be consumed from `FROM gcs`, joined by
the opaque ICU Encounter key, with the target's LEFT JOINs retained.

The GCS Observation mapping uses exact
`mimic-chartevents-d-items` system/code filters for `223900`, `223901`, and
`220739`; `(effective).ofType(dateTime)`; and
`(value).ofType(Quantity).value`. For item `223900`, the source verbal text is
now available at `component.where(code.coding.system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and code.coding.code='223900').value.ofType(string)` and must drive the ETT discriminator. The component is a nullable repeat.

The probe found 9,791/9,791 exact source/FHIR GCS rows, keys, wall-clock
timestamps, numeric values, and displays; component text agreed 3,266/3,266,
including 1,348 `No Response-ETT` and 78 `No Response` rows. ICU Encounter
spine agreement was 140/140. The completed `gcs` attempt_0008 full comparison
reproduced all 1,637,763 rows exactly, so the former dependency gap is gone.
The implementer must remove ambiguity-propagation NULL logic and must not
declare `gcs_unable` unrepresentable. Quantity unit is absent but unused and
source `valueuom` is NULL in the targeted demo rows.

The probe verified that `effective.ofType(dateTime)` is populated for all
9,791 target observations, while Period and instant variants are empty. All
resource/reference ids were used only for opaque equality joins/grouping; no
id was parsed, reconstructed, hashed, guessed, or hardcoded.

The probe wrote and recorded the reusable mapping at
`mimic-iv/concepts_fhir/carryover/first_day_gcs/fhir-prober.md` and appended
the dataset-wide numeric-chartevents component finding to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/first_day_gcs.md`.
