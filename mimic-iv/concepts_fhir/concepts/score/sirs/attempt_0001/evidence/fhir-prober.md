# FHIR-prober evidence — sirs, attempt_0001

The prober used embedded Pathling 9.6.0 on Spark 4.0.2 over the authoritative
demo Delta warehouse, not HTTP Pathling or stale NDJSON. It read the source
analysis, `MIMIC_NOTES.md`, the relevant dependency fragments, and the
completed dependency artifacts.

SIRS consumes published dependency views rather than rederiving them. The
preprocessor exposes `first_day_bg_art`, `first_day_lab`, and
`first_day_vitalsign` with opaque `icu_encounter_key` and `patient_key`
columns, so dependency joins must use equality on `icu_encounter_key` and not
recreate dropped integer IDs. The ICU identity spine maps ICU Encounter
`identifier.value` under the exact ICU identifier system to `stay_id`, its
`subject` reference to Patient identifier value for `subject_id`, and its
`partOf` reference to the hospital Encounter identifier value for `hadm_id`.
All required keys are emitted unchanged and type-prefixed.

The requested dependency fields were checked 140/140 exact against DuckDB:
`pco2_min`, temperature extrema, heart/respiratory-rate maxima, and WBC/bands
extrema. No SIRS-side code filters or new representability gap were found.
The known upstream chartevents DST normalization can be inherited through
`first_day_vitalsign`, but this stage made no terminal decision and did not
append a new dataset-wide fragment.

Reusable mapping was written to
`mimic-iv/concepts_fhir/carryover/sirs/fhir-prober.md` and recorded with
`mimic_utils carryover-record sirs --stage fhir-prober`.
