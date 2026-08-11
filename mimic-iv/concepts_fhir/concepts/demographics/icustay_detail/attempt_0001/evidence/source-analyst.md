## Evidence

Concept: `icustay_detail`.

Read `AGENTS.md`, `MIMIC_NOTES.md`, the relevant `MIMIC_NOTES.d` fragments
(`gcs.md`, `height.md`, `icp.md`, `crrt.md`), the DAG node, and the
authoritative SQL at `mimic-iv/concepts/demographics/icustay_detail.sql`.
Verified the SQL SHA-256 matches the DAG.

The query reads `mimiciv_icu.icustays`, inner-joins
`mimiciv_hosp.admissions` on `hadm_id`, and inner-joins
`mimiciv_hosp.patients` on `subject_id`. It outputs 18 columns including
identifiers, demographics, admission/ICU timestamps, hospital and ICU LOS,
ranks, and first-stay booleans. It has no CTEs, WHERE predicates, time
windows, value constraints, or coded filters; there is no literal code set.
There are no `mimiciv_derived` dependencies or aggregations. Window functions
repeat `DENSE_RANK()` calculations partitioned by patient/admission. The
oracle manifest identifies `stay_id` as the natural key and reports 73,181
rows.

Reusable analysis was written to
`mimic-iv/concepts_fhir/carryover/icustay_detail/source-analyst.md` and
recorded in `mimic-iv/concepts_fhir/carryover/icustay_detail/carryover.json`
via `uv run mimic_utils carryover-record icustay_detail --stage
source-analyst`. No attempt implementation artifacts, `MIMIC_NOTES.md`, or
commits were modified.

Result: `icustay_detail` is a level-0 ICU-stay-grain projection enriched from
admissions and patients, with LOS and stay-order calculations but no coded
filtering or derived dependency.
