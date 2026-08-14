# Source-analyst evidence — rhythm

The source analysis read `mimic-iv/concepts/measurement/rhythm.sql`, the DAG,
MIMIC-IV DDL, the oracle manifest, `MIMIC_NOTES.md`, and relevant provisional
fragments. `rhythm` is dependency-free and reads only
`mimiciv_icu.chartevents`. It filters exact itemids 220048, 224650, 224651,
226479, and 226480 with non-null `stay_id`, groups by `(subject_id, charttime)`,
and emits seven columns: two key columns and five text aggregates. The
`heart_rhythm` field is a distinct lexically ordered `STRING_AGG` with `'; '`;
the four ectopy fields are lexical `MAX` values. The oracle key is
`(subject_id, charttime)` and the expected row count is 5,873,723.

The analysis identified risks from FHIR categorical text, source NULL-row
omission, repeated observations, and DST transformation of the temporal key.
Reusable analysis was written to
`mimic-iv/concepts_fhir/carryover/rhythm/source-analyst.md` and recorded in the
carryover ledger.
