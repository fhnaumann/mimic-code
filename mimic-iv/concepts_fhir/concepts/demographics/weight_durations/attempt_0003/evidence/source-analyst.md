# Source-analyst evidence (reused carryover)

The source-analysis stage was reused from the recorded concept-level carryover
because `mimic_utils carryover` marked it reusable. It identifies
`mimic-iv/concepts/demographics/weight_durations.sql` as a level-0 concept with
no dependencies. The canonical query reads ICU `chartevents` and `icustays`,
filters itemids `226512` and `224639` with positive non-null values below 1500,
constructs admission/daily interval rows with stay-scoped windows and a
possible synthetic pre-first row, and returns `stay_id`, `starttime`,
`endtime`, `weight`, and `weight_type`.

The reusable source analysis is at
`mimic-iv/concepts_fhir/carryover/weight_durations/source-analyst.md`. No new
source analysis was spawned or modified for attempt 0003.
