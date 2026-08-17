Evidence block — source-analyst

Read `mimic-iv/concepts/firstday/first_day_bg.sql`, the DAG entry, the oracle manifest, `MIMIC_NOTES.md`, lab-related provisional fragments, and the completed `bg` dependency analysis. Verified the SQL SHA256 and oracle shape.

The source uses `mimiciv_icu.icustays` and `mimiciv_derived.bg`; it performs one inclusive LEFT JOIN on `subject_id` with the `intime` ± time window, has no WHERE clause, coded filters, ORDER BY, or window functions, groups by `(subject_id, stay_id)`, and takes MIN/MAX over 21 dependency measurements. It emits 44 columns with natural key `stay_id`. The dependency inputs are `subject_id`, `charttime`, and the 21 measurement fields. No coding systems or literal codes occur in this consumer SQL.

Artifacts produced:
- `mimic-iv/concepts_fhir/carryover/first_day_bg/source-analyst.md`
- `mimic-iv/concepts_fhir/carryover/first_day_bg/carryover.json`

No commit made.
