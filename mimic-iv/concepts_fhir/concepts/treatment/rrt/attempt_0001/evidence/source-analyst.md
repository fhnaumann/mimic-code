## Evidence

The source analyst read `mimic-iv/concepts/treatment/rrt.sql:1-327`, the DAG,
the full oracle manifest, source schemas, `MIMIC_NOTES.md`, and relevant
fragments. The concept uses `mimiciv_icu.chartevents`, `inputevents`, and
`procedureevents`; filters the exact itemids and non-null predicates in the
canonical SQL; overlays chart observations with inclusive input/procedure
ranges; and emits `stay_id`, `charttime`, `dialysis_present`,
`dialysis_active`, and `dialysis_type`. There is no natural key, so full-tuple
multiset comparison is required. No derived dependencies or new dataset-wide
quirk were identified.

Produced/reused: `mimic-iv/concepts_fhir/carryover/rrt/source-analyst.md`.
