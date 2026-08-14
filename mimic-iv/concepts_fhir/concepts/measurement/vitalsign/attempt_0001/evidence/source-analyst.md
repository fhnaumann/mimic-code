## Evidence

The source analyst read `mimic-iv/concepts/measurement/vitalsign.sql`, DAG/state metadata, `MIMIC_NOTES.md`, and relevant provisional fragments. The concept is a direct `mimiciv_icu.chartevents` pivot over `subject_id`, `stay_id`, `charttime`, `itemid`, `valuenum`, and `value`, with `stay_id IS NOT NULL` and an exact 19-itemid filter. It has no joins or derived dependencies, uses `AVG`, `MAX`, and `ROUND`, and groups by `(subject_id, stay_id, charttime)` under the `mimic-chartevents-d-items` coding system.

Reusable analysis was written to `mimic-iv/concepts_fhir/carryover/vitalsign/source-analyst.md` and recorded with `carryover-record`. No new dataset-wide quirk was independently verified; no notes fragment was appended.
