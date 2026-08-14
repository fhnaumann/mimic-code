# Source-analyst evidence — creatinine_baseline attempt_0001

The source analyst read the canonical `measurement/creatinine_baseline.sql`,
the DAG node and dependency SQL, the oracle manifest, the LOOP_CONTRACT,
`MIMIC_NOTES.md`, and relevant chemistry/kdigo_creatinine fragments. The
canonical query emits one row per adult `hadm_id`, using `age` and `chemistry`
dependencies, a patient gender join, an admission-level minimum creatinine,
and a CKD flag from ICD-9 prefix `585`/version 9 or ICD-10 prefix `N18`/version
10. It selects measured `scr_min` when <= 1.1 or CKD is present, otherwise a
gender-adjusted MDRD estimate. The manifest shape is seven columns keyed by
`hadm_id`; dependencies are `age` and `chemistry`.

Reusable analysis was written to and recorded from:
`mimic-iv/concepts_fhir/carryover/creatinine_baseline/source-analyst.md`.
No new dataset-wide quirk was discovered, so no notes fragment was appended.
