# Evidence: source-analyst

Concept `invasive_line`, attempt `0001`.

Read the canonical SQL `mimic-iv/concepts/treatment/invasive_line.sql`, DAG metadata, relevant MIMIC DDL, oracle manifest, `MIMIC_NOTES.md`, and the existing notes fragments. Verified a dependency-free level-0 concept using `mimiciv_icu.procedureevents` joined to `mimiciv_icu.d_items`, filtering the exact 24 itemids, applying the source line-type and line-site CASE mappings, and emitting `stay_id`, `line_type`, `line_site`, `starttime`, and `endtime` without aggregation or deduplication. The oracle has 93,378 rows, no natural key, and full-tuple multiset comparison semantics.

Reusable analysis artifact: `mimic-iv/concepts_fhir/carryover/invasive_line/source-analyst.md`.
Carryover ledger: `mimic-iv/concepts_fhir/carryover/invasive_line/carryover.json`.
