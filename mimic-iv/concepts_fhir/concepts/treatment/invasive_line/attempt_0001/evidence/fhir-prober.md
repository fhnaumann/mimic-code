# Evidence: fhir-prober

Concept `invasive_line`, attempt `0001`.

Read the source carryover, curated `MIMIC_NOTES.md`, and relevant provisional fragments. Probed the authoritative local Delta warehouse with embedded Pathling 9.6.0 on Spark 4.0.2 and checked against the read-only demo DuckDB oracle. Mapped ICU `procedureevents` to `Procedure`, exact item codes under `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items`, line labels from `Procedure.code.coding.display`, line site from `bodySite.coding.code`, performed interval endpoints from `performed.ofType(Period).start/end`, and `stay_id` through the ICU Encounter identifier system. Confirmed 216 selected source rows and 216 Procedure resources, 216/216 identifier-based Encounter joins, 140 body-site codings with 76 absent, and exact datetime endpoint recovery before the known whitespace transformation.

Dataset-wide findings appended to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/invasive_line.md`: Procedure identifiers are absent; body-site displays are absent; body-site codes are whitespace-trimmed by the ETL. The reusable mapping is in `mimic-iv/concepts_fhir/carryover/invasive_line/fhir-prober.md` and the carryover ledger is `mimic-iv/concepts_fhir/carryover/invasive_line/carryover.json`.
