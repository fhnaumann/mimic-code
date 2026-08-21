Evidence block

Concept: `kdigo_stages`; attempt: `0002`.

Read and applied `AGENTS.md`, the `fhir-mapping` and `pathling-sql` skills,
the complete `MIMIC_NOTES.md`, the owned `MIMIC_NOTES.d/kdigo_stages.md`
fragment, and the relevant provisional fragments `README.md`, `crrt.md`,
`kdigo_creatinine.md`, `kdigo_uo.md`, `urine_output.md`,
`first_day_urine_output.md`, `weight_durations.md`, and `icustay_times.md`.
Read the authoritative `source-analyst.md` and `fhir-prober.md` carryover,
the canonical source SQL, the `kdigo_stages` manifest entry, and attempt 0001
artifacts including its consumer SQL and mismatch diagnosis. Also checked the
completed `kdigo_uo` attempt 0004 consumer output shape and comparison context.

Produced:
- `ViewDefinition.kdigo_stages_icu_encounter.json`
- `ViewDefinition.kdigo_stages_hospital_encounter.json`
- `ViewDefinition.kdigo_stages_patient.json`
- `concept.sql`

The three ViewDefinitions project the ICU Encounter, hospital Encounter, and
Patient opaque resource/reference keys plus identifier values from the required
identifier systems and ICU `period.start`. The SQL joins dependencies by their
opaque ICU encounter keys, preserves the ICU spine and NULL-preserving joins,
uses the completed `kdigo_creatinine`, `kdigo_uo`, and `crrt` views, retains the
canonical `UNION DISTINCT` event axis and KDIGO CASE branches, and applies the
subject-level six-hour `RANGE` smoothing window. The outer SELECT emits every
manifest column in declared order with an explicit declared-type cast, followed
by the required uncast `patient_key`, `encounter_key`, and `icu_encounter_key`.

No `unrepresentable.json` was needed. No new dataset-wide quirk was established,
so `MIMIC_NOTES.md` and all fragments remain unmodified. The known mapping caveat
is inherited upstream TIMESTAMPTZ/DST-gap normalization of FHIR observation times
and ICU `Encounter.period.start`, which can propagate through dependency windows,
event alignment, and smoothing; no resource-id inversion is used.

Lint result: `uv run mimic_utils lint-sql kdigo_stages` passed cleanly on the
new attempt output. Demo and full-data execution were not run, as requested.
