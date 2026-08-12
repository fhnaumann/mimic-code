# Source-analyst evidence

The source analyst read `mimic-iv/concepts/organfailure/kdigo_creatinine.sql`, verified the DAG path and SHA, and reviewed the relevant schema and dataset notes. The concept uses `icustays` and `labevents` itemid `50912`, filters numeric values at `<= 150` over the inclusive ICU-relative seven-day window, averages by `(stay_id, charttime)`, and computes left-preserving prior 48-hour and seven-day minima. The six output columns are `hadm_id`, `stay_id`, `charttime`, `creat`, `creat_low_past_48hr`, and `creat_low_past_7day`; the manifest uses full-tuple multiset comparison with no natural key.

Reusable analysis: `mimic-iv/concepts_fhir/carryover/kdigo_creatinine/source-analyst.md`.
