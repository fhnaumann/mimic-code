Evidence block — source-analyst

The source analyst read AGENTS.md, the concept DAG, canonical SQL at
`mimic-iv/concepts/measurement/ventilator_setting.sql`, MIMIC_NOTES.md,
relevant MIMIC_NOTES.d fragments, and the ICU schema DDL. The source is based
on `mimiciv_icu.chartevents`, with no joins or mimiciv_derived dependencies.
It filters non-NULL value/stay_id rows and exact ventilator itemids, applies
FIO2/PEEP value cleaning, then groups by `subject_id, charttime` and pivots
with MAX. The source uses exact chartevents itemid literals and does not name
an explicit coding-system URI.

Reusable analysis was written and recorded at
`mimic-iv/concepts_fhir/carryover/ventilator_setting/source-analyst.md`.
