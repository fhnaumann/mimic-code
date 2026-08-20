## Evidence

The prober mapped ICU `icustays` to ICU Encounter, filtered by the
`.../encounter-icu` identifier system, and mapped the five derived lab
dependencies to their completed published views: `complete_blood_count`,
`chemistry`, `blood_differential`, `coagulation`, and `enzyme`. It verified
the identifier spine, opaque resource keys, `period.start` as `TIMESTAMP_NTZ`,
and dependency `charttime`/analyte projections. Embedded Pathling preprocessing
verified dependency row counts CBC 2,959; chemistry 3,289; differential 2,763;
coagulation 1,630; enzyme 1,411, with required patient/time/analyte columns.

The ICU probe found 140/140 ICU keys, patient keys, stay identifiers, and
`intime` values; DuckDB agreement for stay ID, subject ID, and `intime` was
140/140. An in-memory candidate using the published dependency views matched
all 140 demo ICU stays and all 88 manifest columns, including nulls. Required
types were identified as integer identifiers, 76 DOUBLE aggregates, 10
DECIMAL(38,4) differential absolute-count columns, and opaque string keys.

The prober checked relevant curated and provisional notes, including the
labevents/Encounter DST normalization leads. It found no new dataset-wide
quirk and appended nothing to `MIMIC_NOTES.d/first_day_lab.md`.

Reusable analysis was written to
`mimic-iv/concepts_fhir/carryover/first_day_lab/fhir-prober.md` and recorded
with `mimic_utils carryover-record first_day_lab --stage fhir-prober`.
