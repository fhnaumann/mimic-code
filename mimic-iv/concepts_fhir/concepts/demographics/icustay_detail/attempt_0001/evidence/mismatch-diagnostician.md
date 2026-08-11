## Evidence

Diagnosed attempt 0001's `review`, tier `contested`, from
`comparison.full.json`, all attempt ViewDefinitions and SQL, canonical source
SQL, oracle manifest, carryover/evidence, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`,
all current fragments, and the relevant upstream `mimic-fhir/sql` files.

The 13,491 conflicts include two already attributed DST rows and 13,489
residuals. The diagnosis is a fixable bug requiring retry before judging:

- `race`: the implementation decoded only four demo-observed values and
  omitted the ethnicity extension. Add the US Core ethnicity text projection
  and decode both extensions. Of the residual race conflicts, 1,766 are
  fixable; the remainder are intrinsic latest-admission selection and
  many-to-one OMB collapse from `mimic-fhir/sql/fhir_patient.sql:17,23-30,59,110`,
  `fn/fn_patient_extension.sql:11-27,31-47`,
  `fhir_etl/map_race_omb.sql:13-45`, and `fhir_etl/map_ethnicity.sql:13-47`.
- `hospital_expire_flag`: the SQL manufactured a DOD-in-admission-window
  estimate. The source flag and admission death time are not serialized by
  `fhir_patient.sql:52,109` or `fhir_encounter.sql:59-71,149-169`. Replace it
  with `CAST(NULL AS SMALLINT)` and declare it in `unrepresentable.json`.
- `admission_age`: intrinsic birthDate transformation loss from
  `fhir_patient.sql:15,108`; current FHIR-side computation is faithful.
- `admittime`, `dischtime`, `icu_intime`: intrinsic DST-gap normalization from
  `fhir_encounter.sql:65-66,149-152` and
  `fhir_encounter_icu.sql:31-32,44,97-100`; keep `TIMESTAMP_NTZ` parsing.
- `los_icu`: the ten conflicts derive from shifted ICU starts; source `icu.los`
  is not serialized (`fhir_encounter_icu.sql:33,69-120`), so the current
  period-derived value is faithful.

Invalidate `fhir-prober` because it over-generalized the four demo race values,
omitted ethnicity, and recommended an inexact expiry heuristic. Do not
invalidate `source-analyst`.

Dataset-wide sections appended to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/icustay_detail.md`:

- Correction: Patient race is latest-admission and many-to-one OMB mapped.
- Hospital expiry and admission death time are not serialized into FHIR.
- Correction: hospital expiry must be a declared typed NULL, not a DOD
  estimate.

The next attempt must fix race/ethnicity and typed-null expiry; the remaining
conflicts should then be presented to the equivalence judge with the cited
upstream ETL statements.
