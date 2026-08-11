## Evidence

The equivalence judge reviewed attempt 0003 as a mandatory `review`, tier
`contested`, with no divergent dependencies. It read `LOOP_CONTRACT.md`,
curated `MIMIC_NOTES.md`, the oracle manifest, canonical source SQL, all
attempt 0003 implementation/full-run/evidence artifacts, attempts 0001–0002
history, carryovers, and the cited upstream ETL files.

Verdict: `accept`.

The judge confirmed no fixable bug remains. The 11,501 race conflicts are
explained by latest-admission selection and many-to-one OMB race/ethnicity
serialization in `mimic-fhir/sql/fhir_patient.sql:17,23-30,59,110`,
`fn/fn_patient_extension.sql:11-47,60-63`,
`fhir_etl/map_race_omb.sql:13-45`, and
`fhir_etl/map_ethnicity.sql:13-47`; the detailed admission-specific value is
not recoverable from FHIR. The 86 admission-age conflicts arise from
synthesized `Patient.birthDate` at `fhir_patient.sql:15,108`. Endpoint and ICU
LOS conflicts arise from irreversible TIMESTAMPTZ period transforms at
`fhir_encounter.sql:65-66,149-152` and
`fhir_encounter_icu.sql:31-32,44,97-100`, with source ICU LOS selected at line
33 but not serialized. The typed-NULL `hospital_expire_flag` declaration is
valid because the source flag/admission death time are omitted by
`fhir_patient.sql:52,109` and `fhir_encounter.sql:59-71,149-169`.

All 73,181 rows/keys were preserved with no invented or missing rows. Overall
identical fidelity is 0/73,181 because expiry is NULL by declaration; fidelity
on representable columns is 61,587/73,181 (84.16%). The judge found the
divergence intrinsic but not severe enough to block. No files were modified.
