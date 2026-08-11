## Evidence

Re-probed `icustay_detail` against the authoritative demo Delta with embedded
Pathling 9.6.0/Spark 4.0.2 and DuckDB after invalidating the prior carryover.
Read `MIMIC_NOTES.md`, the append-only icustay_detail fragment, source
carryover, and the previous probe as a hypothesis only.

Confirmed ICU Encounter (`.../encounter-icu`), hospital Encounter
(`.../encounter-hosp`), and Patient mappings, identifier spines, subject and
parent Encounter joins, periods, gender, death date, and typed casts. Rechecked
race and ethnicity extensions: race OMB values include `2054-5`, `2106-3`,
`ASKU`, and `UNK`; ethnicity includes `2135-2`, `2186-5`, and null. The full
ETL-supported race categories include Asian, American Indian/Alaska Native,
Native Hawaiian/Pacific Islander, and `other`.

Confirmed `anchor_age`/`anchor_year` have no direct FHIR paths, and
`hospital_expire_flag`/`deathtime` have no FHIR equivalent; the implementation
must emit typed NULL for hospital expiry. Derived LOS, age, ranks, and first
stay flags agreed with the 140-row demo oracle for every representable output.

The corrected reusable mapping was written to
`mimic-iv/concepts_fhir/carryover/icustay_detail/fhir-prober.md` and recorded
in its carryover ledger. A dataset-wide section, “US Core race and ethnicity
OMB categories are Coding extension values”, was appended to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/icustay_detail.md`. No attempt artifacts
or commits were modified.
