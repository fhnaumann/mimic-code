# Source analyst evidence — icustay_hourly

Read the canonical concept SQL, DAG/source context, dependency SQL, shared
`MIMIC_NOTES.md`, oracle manifest, and the empty attempt directory. The DAG
SHA matched. `icustay_hourly` depends on `mimiciv_derived.icustay_times` and
consumes only `stay_id`, `intime_hr`, and `outtime_hr`; it has no direct raw
table joins, target filters, coding literals, or aggregations. Its rows are
generated over first/last heart-rate observation times, not ICU Encounter
periods. The dependency uses `mimiciv_icu.chartevents.itemid = 220045`.

The natural key is `(stay_id, endtime)` and the output types are `INTEGER`,
`BIGINT`, and `TIMESTAMP`. No new dataset-wide quirk was established; the
existing datetime/DST notes are relevant but were not appended. Reusable
analysis was recorded in carryover.

Artifacts:
- `mimic-iv/concepts_fhir/carryover/icustay_hourly/source-analyst.md`
- `mimic-iv/concepts_fhir/carryover/icustay_hourly/carryover.json`
- Attempt: `mimic-iv/concepts_fhir/concepts/demographics/icustay_hourly/attempt_0001/`
