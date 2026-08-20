## Evidence

The source analyst read the canonical SQL, DAG entry, `LOOP_CONTRACT.md`,
`MIMIC_NOTES.md`, and relevant provisional fragments. The SQL uses
`mimiciv_icu.icustays` plus derived dependencies `complete_blood_count`,
`chemistry`, `blood_differential`, `coagulation`, and `enzyme`. It has
patient/time-window LEFT JOINs, no WHERE or coded filters, five `GROUP BY
stay_id` CTEs with MIN/MAX aggregations, and an 88-column stay-level output.
No itemids, ICD codes, or coding systems are present. The existing curated lab
DST-normalization quirk is relevant; no new dataset-wide note was identified.

Reusable analysis was written to
`mimic-iv/concepts_fhir/carryover/first_day_lab/source-analyst.md` and recorded
with `mimic_utils carryover-record first_day_lab --stage source-analyst`.
