## Evidence

Concept: `oxygen_delivery`.

Read `mimic-iv/concepts/measurement/oxygen_delivery.sql`, `concept_dag.json`,
`MIMIC_NOTES.md`, all existing `MIMIC_NOTES.d` fragments, chartevents DDL and
generated SQL, downstream `ventilation.sql`, and the chartevents FHIR ETL.

The source reads only `mimiciv_icu.chartevents` and has no derived dependencies.
It uses `subject_id`, `stay_id`, `charttime`, `itemid`, `value`, `valuenum`,
`valueuom`, and `storetime`; deduplicates with `ROW_NUMBER()`; filters exact
itemids `223834`, `227582`, `227287`, `226732`; and groups by
`subject_id, charttime`. The result is one row per patient/time with oxygen
flow values and four ranked device strings. Main mapping risks are
DST-normalized FHIR chart times, `storetime` ranking, categorical `valueString`,
and the source omission of `stay_id` from partitions, joins, and grouping.

Reusable analysis was written to
`mimic-iv/concepts_fhir/carryover/oxygen_delivery/source-analyst.md` and
recorded with `mimic_utils carryover-record oxygen_delivery --stage
source-analyst`.
