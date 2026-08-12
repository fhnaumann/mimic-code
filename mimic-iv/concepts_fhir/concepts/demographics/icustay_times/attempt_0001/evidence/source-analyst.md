# Source analyst evidence

Concept: `icustay_times`; attempt: `0001`.

Read and checked the canonical SQL, DAG metadata, `LOOP_CONTRACT.md`,
`MIMIC_NOTES.md`, and the relevant `MIMIC_NOTES.d/icustay_detail.md` fragment.

The source uses `mimiciv_icu.chartevents` and `mimiciv_icu.icustays`, filters
exactly `itemid = 220045`, aggregates `MIN(charttime)` as `intime_hr` and
`MAX(charttime)` as `outtime_hr` by `stay_id`, then LEFT JOINs that aggregate
to ICU stays. Output columns are integer `subject_id`, `hadm_id`, `stay_id`
and timestamp `intime_hr`, `outtime_hr`; the natural key is `stay_id`. The
DAG reports 73,181 oracle rows, level 0, with no derived dependency.

Reusable analysis was written to:
`mimic-iv/concepts_fhir/carryover/icustay_times/source-analyst.md`.

No new dataset-wide quirk was established. Existing datetime guidance in
`MIMIC_NOTES.md` is relevant to the FHIR mapping.
