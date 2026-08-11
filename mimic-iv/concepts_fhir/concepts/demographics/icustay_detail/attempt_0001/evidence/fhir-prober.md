## Evidence

Concept: `icustay_detail`.

Read `AGENTS.md`, `MIMIC_NOTES.md`, the source analysis, the canonical
Observation ViewDefinition, and existing `MIMIC_NOTES.d` fragments. The
curated notes on identifier values, Encounter stream filtering, extensions,
`Patient.birthDate`, and `TIMESTAMP_NTZ` changed mapping decisions.

Mappings confirmed against the authoritative demo Delta:

- ICU `Encounter` filtered by identifier system `.../encounter-icu` supplies
  `stay_id`, ICU period, subject reference, and `partOf` hospital reference.
- Hospital `Encounter` filtered by `.../encounter-hosp` supplies `hadm_id`,
  hospital period, and subject reference.
- `Patient` supplies subject identifier, gender, death date, birthDate, and
  race extension.
- Identifiers use `identifier.value` and must be cast to INTEGER. Datetimes
  use `CAST(... AS TIMESTAMP_NTZ)`. `gender` maps `male/female` to `M/F`.
- Source output derivations include hospital/ICU LOS, admission age, hospital
  and ICU stay ranks, first-stay booleans, and hospital expiration flag.

Probe counts: Patient identifiers/gender/birthDate/race were 100/100
populated; death date was 31/100. Hospital Encounter identifiers, subject
references, and periods were 275/275. ICU Encounter identifiers, subject
references, `partOf`, and periods were 140/140. Encounter class was not used
as a discriminator and there are no coded filters.

Demo oracle comparison found 140/140 exact for identifiers, gender, death
date, admission/discharge times, admission age, ICU times, both LOS fields,
both rank pairs, and both boolean flags. Race text was not exact because the
FHIR Patient extension collapses detailed admission-specific race to four
broad values; broad normalization reached 122/140. Hospital expiration was
derived exactly on the demo cohort. Admission age is only approximately
recoverable in general because `anchor_age`/`anchor_year` are not served;
curated full-data evidence reports 460 conflicts among 431,231 admissions for
the related age derivation. DST-gap timestamps are irreversibly normalized by
the upstream Encounter ETL.

The reusable mapping was written to
`mimic-iv/concepts_fhir/carryover/icustay_detail/fhir-prober.md` and recorded
with `uv run mimic_utils carryover-record icustay_detail --stage fhir-prober`.
The dataset-wide finding “Patient race extension collapses admission race to
four broad values” was appended to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/icustay_detail.md`. No implementation
artifacts or commits were created.
