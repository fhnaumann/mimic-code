Evidence block — `code_status`, attempt 0003

Read and checked `AGENTS.md`, `LOOP_CONTRACT.md`, the complete `MIMIC_NOTES.md`, canonical source SQL, manifest entry, reusable source-analyst/fhir-prober carryover, prior attempts, and all `MIMIC_NOTES.d/*.md` fragments. JSON artifacts passed syntax validation; only new attempt files were created.

Mapping preserves the 8-column full-tuple multiset shape. Four ViewDefinitions cover chart `Observation`, `Patient`, ICU `Encounter`, and hospital `Encounter`. Chart filtering uses the exact chartevents system plus code `223758`; identifiers come from `identifier.value`, with UUID keys used only for joins. Datetimes use `TRY_CAST(... AS TIMESTAMP_NTZ)` with polymorphic coalescing, retaining the prior UUID-witness DST corrections. The hospital POE branch is omitted because it has no exact served FHIR representation and is not mapped to `MedicationRequest`.

Created:
- `ViewDefinition.cs_chart.json`
- `ViewDefinition.cs_patient.json`
- `ViewDefinition.cs_icu.json`
- `ViewDefinition.cs_hosp.json`
- `concept.sql`

No `unrepresentable.json` was created: the POE issue is a row-level coverage gap, while every output column has a chart-Observation representation; declaring any column unrepresentable would be comparator-incompatible.

No new dataset-wide quirk was appended to `MIMIC_NOTES.d/code_status.md`.
