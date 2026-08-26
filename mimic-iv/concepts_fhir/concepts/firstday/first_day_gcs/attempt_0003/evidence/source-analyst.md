# Source analyst evidence — `first_day_gcs`, attempt 0003

The source-analysis stage was reused from the recorded carryover because the
canonical source SQL and its dependency boundary are unchanged. The reusable
analysis is `mimic-iv/concepts_fhir/carryover/first_day_gcs/source-analyst.md`.

It identifies `mimiciv_icu.icustays` as the direct source and the completed
`mimiciv_derived.gcs` concept as the only dependency. The target preserves one
row per ICU `stay_id`, left joins dependency rows in the inclusive
`intime - 6 hours` through `intime + 1 day` window, then selects
`ROW_NUMBER() = 1` by lowest `gcs`, breaking ties with latest `charttime`. The
output columns are `subject_id`, `stay_id`, `gcs_min`, `gcs_motor`,
`gcs_verbal`, `gcs_eyes`, and `gcs_unable`; the FHIR port additionally emits
the required opaque `patient_key` and `icu_encounter_key` companions.

The source analysis records the exact upstream GCS itemids (`223900`, `223901`,
`220739`) and the `No Response-ETT` branch, but does not make a
representability or terminal decision. The current fhir-prober revalidated
that branch against the rebuilt served data and found the dependency fully
representable.

No source-analyst subagent was rerun, no immutable prior attempt was edited,
and no source artifact was newly authored beyond this current-attempt evidence
record.
