# Source analyst evidence

Concept: `first_day_vitalsign`

The source analyst read `mimic-iv/concepts/firstday/first_day_vitalsign.sql`,
the DAG metadata, `MIMIC_NOTES.md`, and nearby concept sources. The canonical
SQL SHA256 was checked against the DAG. The concept is level 1 and depends on
the completed `vitalsign` concept; candidate SQL must consume the preprocessed
`vitalsign` view rather than rederive it.

The source has one row per ICU stay from `mimiciv_icu.icustays`, preserving all
stays with a LEFT JOIN on `stay_id` to `vitalsign` rows in the inclusive window
`[intime - 6 hours, intime + 1 day]`, then grouping by `(subject_id, stay_id)`.
It computes MIN, MAX, and AVG for heart rate, SBP, DBP, MBP, respiratory rate,
temperature, SpO2, and glucose, producing 26 output columns. The dependency
already groups chartevents at `(subject_id, stay_id, charttime)` and applies
the exact vital-sign itemid/value predicates, including Fahrenheit/Celsius
temperature conversion and rounding.

Reusable analysis was written and recorded at
`mimic-iv/concepts_fhir/carryover/first_day_vitalsign/source-analyst.md`.
No attempt artifacts were created by the source analyst.
