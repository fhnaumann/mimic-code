# Source-analyst evidence

Concept: `oasis`; attempt: `0001`.

The source analyst read the DAG node and canonical SQL
`mimic-iv/concepts/score/oasis.sql`, the five direct dependency SQL files and
the relevant transitive measurement SQL, source schema DDL, the full oracle
manifest, `MIMIC_NOTES.md`, and the relevant `MIMIC_NOTES.d/` leads.

The analysis found a one-row-per-ICU-stay OASIS score with natural key
`stay_id`, identifiers `subject_id` and `hadm_id`, five required derived
dependency boundaries (`age`, `first_day_gcs`, `first_day_urine_output`,
`first_day_vitalsign`, and `ventilation`), hospital/ICU source joins, service
and ventilation interval predicates, first-day windows, exact score
thresholds, and the 25-column final schema. It preserved the source's exact
literal filters and noted that no item/code filter appears in OASIS itself.
Resource-key output columns are required by the manifest and must remain
opaque.

Reusable analysis artifact written and recorded:
`mimic-iv/concepts_fhir/carryover/oasis/source-analyst.md` and
`mimic-iv/concepts_fhir/carryover/oasis/carryover.json`.
No ViewDefinition, `concept.sql`, execution, or commit was performed by this
stage.
