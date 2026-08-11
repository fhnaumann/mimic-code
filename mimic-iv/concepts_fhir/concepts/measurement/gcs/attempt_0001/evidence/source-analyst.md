# Source-analyst evidence — gcs attempt_0001

Read the canonical `mimic-iv/concepts/measurement/gcs.sql`, DAG metadata and
oracle manifest, source DDL, `AGENTS.md`, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`,
and the existing `MIMIC_NOTES.d` fragments. The concept is dependency-free and
reads only `mimiciv_icu.chartevents`, filtering itemids `223900`, `223901`, and
`220739`, with the exact sentinel `No Response-ETT`. It pivots by
`(subject_id, stay_id, charttime)`, carries values from the immediately prior
same-stay row within six hours, and emits eight columns keyed by
`(stay_id, charttime)`.

The reusable analysis was written to
`mimic-iv/concepts_fhir/carryover/gcs/source-analyst.md` and recorded with the
carryover ledger. The analysis also identified the dataset-wide chartevents
ETL omission of source rows where `value IS NULL`; this was appended to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/gcs.md` as a provisional finding.

No attempt implementation artifacts were created or changed by this stage.
