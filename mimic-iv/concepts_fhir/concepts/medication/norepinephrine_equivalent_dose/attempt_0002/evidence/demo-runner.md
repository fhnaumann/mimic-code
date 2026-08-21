# Demo runner evidence

The corrected attempt executed successfully with embedded Pathling 9.6.0 on
Spark over the authoritative demo Delta. The `encounter_icu` ViewDefinition
and completed `vasoactive_agent` dependency registered and ran without error.

The persisted shape verdict is `shape_ok` / MAY PROCEED TO FULL DATA. Candidate
ordinary columns were `stay_id` (int/INTEGER), `starttime` and `endtime`
(`timestamp_ntz`/TIMESTAMP), and `norepinephrine_equivalent_dose`
(`decimal(38,4)`/DECIMAL(38,4)). Required opaque support keys
`icu_encounter_key` and `patient_key` were present; no columns were missing,
unexpected, or type-incompatible. Demo row count was 1,748, reported only as
non-gating evidence against the full oracle count of 619,330.

The authoritative artifacts are:
`attempt_0002/candidate.demo.parquet` and `attempt_0002/shape.demo.json`.
A subsequent duplicate invocation was refused by write-once protection; it
did not alter the authoritative successful artifacts.
