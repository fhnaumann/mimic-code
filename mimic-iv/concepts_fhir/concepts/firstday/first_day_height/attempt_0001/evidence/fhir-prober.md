# FHIR prober evidence — `first_day_height`

Read the source carryover, completed `height` dependency carryover and
attempt_0004 artifacts, curated `MIMIC_NOTES.md`, and the provisional
`height`, `weight_durations`, and `icustay_times` fragments. Probed the
authoritative demo Delta with embedded Pathling 9.6.0/Spark 4.0.2 and checked
against the read-only DuckDB demo oracle.

The ICU stay spine maps to `Encounter` selected by
`identifier.system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'`.
Use `getResourceKey()` as `icu_encounter_key`,
`subject.getReferenceKey(Patient)` as `patient_key`, and the ICU identifier
value as `stay_id_str` cast to INTEGER. `period.start` is the `intime`
representation and must be cast directly to `TIMESTAMP_NTZ`. Patient
`identifier.value` under the patient identifier system supplies `subject_id`
and must also be cast to INTEGER. The required resource/reference keys are
emitted verbatim; ids are opaque and used only for equality joins.

The completed `height` dependency (attempt_0004) publishes
`charttime TIMESTAMP_NTZ`, `height DECIMAL(38,2)`, `patient_key STRING`, and
`icu_encounter_key STRING`, with `subject_id`/`stay_id` stripped at the
dependency boundary. Therefore the target must consume `FROM height`, join on
`height.icu_encounter_key = icu_encounter_key`, apply the inclusive window,
and not rederive or join the dependency by `stay_id`.

For dependency audit, height Observations use the exact chartevents system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` and
codes `226707`/`226730`; both had 71/71 source/FHIR rows and combined
cardinality 142/142. Effective `dateTime` and Quantity value aliases are
strings and require `TIMESTAMP_NTZ`/numeric casts; instant and Period choices
were empty for the target. ICU Encounter and Patient joins were 140/140, and
target Observation references were 142/142. The demo dependency agreement was
69/69 and the reproduced first-day table was 140/140, including 74 NULL
heights, but no demo boundary rows exercised the time window.

The probe confirmed the curated DST warning: served ICU/Observation times may
irreversibly normalize spring-forward wall times. This could affect window
membership or averages on full data; no terminal judgment was made here. No
new dataset-wide quirk was found and no `MIMIC_NOTES.d/first_day_height.md`
entry was appended. Reusable findings are at
`mimic-iv/concepts_fhir/carryover/first_day_height/fhir-prober.md`.
