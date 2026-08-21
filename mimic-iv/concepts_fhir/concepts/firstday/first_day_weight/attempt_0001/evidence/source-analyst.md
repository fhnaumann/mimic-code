Evidence block

The source analyst read `mimic-iv/concepts/firstday/first_day_weight.sql`, the
DAG dependency metadata, `MIMIC_NOTES.md`, and the provisional
`MIMIC_NOTES.d/weight_durations.md` lead. The concept is one row per ICU stay,
using `icustays` left-joined to the completed `weight_durations` dependency on
`stay_id` with the inclusive predicate `starttime <= intime + 1 day`; it emits
`subject_id`, `stay_id`, `weight_admit`, `weight`, `weight_min`, and `weight_max`.
The dependency is consumed as a table and supplies the exact source itemids
226512 (admit) and 224639 (daily), with its own source filtering and rounding.
No target-level WHERE clause, lower time bound, or other dependency exists.

Reusable analysis was written to
`mimic-iv/concepts_fhir/carryover/first_day_weight/source-analyst.md` and
recorded with the carryover ledger. No commit was made.
