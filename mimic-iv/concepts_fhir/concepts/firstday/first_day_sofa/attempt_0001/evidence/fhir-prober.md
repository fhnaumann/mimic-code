# FHIR prober evidence — `first_day_sofa`

## Findings

- ICU identity spine mapped through `Encounter`: `subject.getReferenceKey(Patient)` → `patient_key`, ICU identifier system → `stay_id_str`, `partOf.getReferenceKey(Encounter)` → hospital `encounter_key`/`hadm_id_str`, `getResourceKey()` → `icu_encounter_key`, and `period.start` → `intime_datetime`. Demo verification was 140/140 exact for `subject_id`, `hadm_id`, `stay_id`, and wall-clock `intime`.
- All ten canonical dependencies must be consumed as completed derived views: `bg`, four vasoactive views, `ventilation`, `first_day_vitalsign`, `first_day_lab`, `first_day_urine_output`, and `first_day_gcs`.
- Vasoactive ICU medication coding used system `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu`; exact item codes/counts were norepinephrine `221906`/947, epinephrine `221289`/36, dobutamine `221653`/44, dopamine `221662`/28, with coding/resource ratio 1.000.
- Needed event paths include `effective.ofType(dateTime)`, `effective.ofType(Period).start/end`, `(dosage.rate).ofType(Quantity).value`, and `(value).ofType(Quantity).value`; numeric aliases require casts and FHIR datetimes require `TIMESTAMP_NTZ`.
- Required identifier path names and opaque-key outputs follow the canonical `select.column` convention. Identifier values are strings and must be cast to integer output columns; resource/reference keys remain unmodified opaque strings.
- No new dataset-wide quirk was discovered, so `MIMIC_NOTES.d/first_day_sofa.md` was not appended.

## Evidence block

Read/checks: read `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, relevant `MIMIC_NOTES.d` fragments, source carryover, dependency carryover analyses, and current FHIR/ETL data. Probed the authoritative demo Delta with embedded Pathling/Spark and checked identity, coding systems/counts, effective-time variants, quantity paths, and dependency boundaries. Produced reusable mapping at `mimic-iv/concepts_fhir/carryover/first_day_sofa/fhir-prober.md` and recorded `carryover/first_day_sofa/carryover.json`. No ViewDefinition or SQL was authored and no commit was made.
