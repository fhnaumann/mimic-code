# Mismatch-diagnostician evidence — `icustay_detail`, attempt 0004

- Diagnosed the `review`/`contested` result from `comparison.full.json`; no new attempt is warranted and neither carryover stage should be invalidated.
- Confirmed 73,181 keyed rows, schema identity, no only-oracle/only-candidate rows, 11,594 conflict rows, and 61,587 declared-null-only rows.
- `race` (11,501) is upstream latest-admission selection plus many-to-one OMB loss: `mimic-fhir/sql/fhir_patient.sql:10-33,59,110`, `fn/fn_patient_extension.sql:11-47,60-63`, `fhir_etl/map_race_omb.sql:13-45`, and `map_ethnicity.sql:13-47`. The detailed/current admission value is not recoverable from FHIR.
- `admission_age` (86) is upstream loss from synthesized `Patient.birthDate`: `fhir_patient.sql:14-15,108`; `anchor_age`/`anchor_year` are not serialized.
- `admittime`/`dischtime` conflicts are from the upstream `TIMESTAMPTZ` cast and serialization at `fhir_encounter.sql:65-66,149-152`; two rows were attributed by the comparator and five residual conflict cells remain in rows with other conflicts.
- `icu_intime` (10) is from `fhir_encounter_icu.sql:31-32,97-100`; resource identity is opaque and cannot recover the original DST-gap wall time.
- `los_icu` (10) is secondary to the shifted ICU start; source `icustays.los` selected at `fhir_encounter_icu.sql:33` is not serialized, while attempt SQL recomputes LOS from served endpoints.
- Typed-NULL `hospital_expire_flag` is correct: `fhir_encounter.sql:59-71,149-170` and `fhir_patient.sql:52,109` serialize neither admission expiry nor admission death time.
- The reopened paired key additions changed no compared values; attempts 0003 and 0004 have identical divergence counts.
- No dataset-wide fragment section was appended. Existing owned-fragment leads were independently verified against curated notes and ETL.

Recommendation: route directly to the equivalence judge; do not retry.
