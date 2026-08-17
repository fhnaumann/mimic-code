# Equivalence-judge evidence — `icustay_detail`, attempt 0004

- Independent judge verdict: `accept` for the `contested` review.
- The judge confirmed all 73,181 ICU-stay keys are preserved with no only-oracle or only-candidate rows.
- Upstream citations accepted: `mimic-fhir/sql/fhir_patient.sql:10-33,52,59,108-110`; `fn/fn_patient_extension.sql:11-47,60-63`; `fhir_etl/map_race_omb.sql:13-45`; `fhir_etl/map_ethnicity.sql:13-47`; `fhir_encounter.sql:59-71,149-170`; and `fhir_encounter_icu.sql:31-33,69-120`.
- The 11,501 race conflicts are latest-admission/many-to-one OMB loss; 86 admission-age conflicts are synthesized-birthDate loss; endpoint and LOS conflicts are irreversible upstream datetime transformation loss; and typed-NULL `hospital_expire_flag` is an absent admission-level element.
- Essentiality check passed: no missing value changes ICU-stay row inclusion, keys, grouping, rankings, carry-forward, or table grain. Representable fidelity is 61,587/73,181 (84.1571%); the declared expiry column accounts for the all-row NULL divergence classification.
- No divergent dependencies. No new notes fragment entry was required.

The exact judge justification is recorded in the task evidence and was used for `mimic_utils accept-divergence`.
