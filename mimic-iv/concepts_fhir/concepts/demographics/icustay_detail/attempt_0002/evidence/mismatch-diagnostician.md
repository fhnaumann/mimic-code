## Evidence

Diagnosed attempt 0002's contested review from its comparison, implementation,
declaration, prior attempt history, source/manifest, notes, and relevant
`mimic-fhir/sql` ETL statements.

The attempt contains one fixable implementer bug: `concept.sql:7-26,33-52`
wraps datetime values in `TRY_TO_TIMESTAMP(REGEXP_REPLACE(...), fixed_format)`
before casting to `TIMESTAMP_NTZ`. That timezone-aware intermediate reintroduces
DST normalization. The correction is to use bare
`TRY_CAST(period_start AS TIMESTAMP_NTZ)` / `TRY_CAST(period_end AS
TIMESTAMP_NTZ)` for all four endpoints. This explains the regression versus
attempt 0001: added conflicts in `admittime`, `dischtime`, `icu_intime`,
`icu_outtime`, and derived `los_icu` at `concept.sql:130-136`.

After that correction, intrinsic residuals are supported by upstream ETL:

- Race (11,501): latest-admission selection and many-to-one OMB mapping in
  `mimic-fhir/sql/fhir_patient.sql:17,24-30,59,110`,
  `fn/fn_patient_extension.sql:11-47,60-63`,
  `fhir_etl/map_race_omb.sql:13-45`, and
  `fhir_etl/map_ethnicity.sql:13-47`; earlier/admission-specific detailed race
  is unrecoverable from Patient extensions and Encounter has no race.
- Admission age (86): `fhir_patient.sql:15,108` synthesizes and stores only
  transformed `Patient.birthDate`, omitting `anchor_age` and `anchor_year`.
- Hospital/ICU endpoint conflicts: `fhir_encounter.sql:65-66,74,149-152` and
  `fhir_encounter_icu.sql:31-32,44,97-100` irreversibly cast wall times through
  TIMESTAMPTZ while retaining no pre-cast witness.
- ICU LOS (baseline 10): `fhir_encounter_icu.sql:33,69-120` does not serialize
  source `icu.los`; only transformed period endpoints remain.

The typed-NULL `hospital_expire_flag` declaration is valid. The source flag
and admission `deathtime` are omitted by `fhir_patient.sql:52,109` and
`fhir_encounter.sql:59-71,149-169`; the comparator reported no declaration
violation.

Recommendation: retry only the datetime casts; no carryover stage is at fault.
The dataset-wide section “ICU Encounter serializes transformed period
endpoints but omits source ICU LOS” was appended to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/icustay_detail.md`.
