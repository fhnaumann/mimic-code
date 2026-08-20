# Source-analyst evidence — `first_day_rrt`

Read the canonical `mimic-iv/concepts/firstday/first_day_rrt.sql`, DAG metadata,
source DDL, `MIMIC_NOTES.md`, and relevant provisional fragments including
`MIMIC_NOTES.d/rrt.md`, `crrt.md`, and `icustay_times.md`.

The source reads `mimiciv_icu.icustays` and the completed `mimiciv_derived.rrt`
dependency. It preserves one row per ICU stay via a LEFT JOIN on `stay_id` and
an inclusive window from six hours before `icustays.intime` through one day
after it. It groups by `(subject_id, stay_id)`, applies `MAX` to
`dialysis_present` and `dialysis_active`, and produces an ordered distinct
comma-space `STRING_AGG` of `dialysis_type`. There are no direct coded filters;
the dependency boundary must remain intact and candidate SQL must consume the
preprocessed `rrt` view rather than rederive it.

The reusable analysis was written to
`mimic-iv/concepts_fhir/carryover/first_day_rrt/source-analyst.md` and recorded
with `mimic_utils carryover-record`. No new dataset-wide quirk was established
at this stage; the relevant existing notes concern retained repeated chartevent
rows and upstream DST normalization.
