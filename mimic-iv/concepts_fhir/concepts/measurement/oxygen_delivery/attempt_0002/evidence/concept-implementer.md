# Evidence: concept-implementer

Concept: `oxygen_delivery`; attempt: `0002`.

The implementer read the canonical SQL, reusable source analysis and FHIR mapping, curated MIMIC notes, and the oxygen-delivery fragment. It produced the three ViewDefinitions and `concept.sql` in this attempt. JSON validation and `uv run mimic_utils lint-sql oxygen_delivery` passed. The implementation preserves exact chartevents coding filters, resource multiplicity, issued/storetime ranking, flow-code merging, flow-driven join semantics, opaque identity joins, `TIMESTAMP_NTZ`, and bounded Spark VARCHAR casts. No new dataset-wide quirk was found.

Artifacts:

- `ViewDefinition.oxygen_delivery_observation.json`
- `ViewDefinition.oxygen_delivery_patient.json`
- `ViewDefinition.oxygen_delivery_encounter.json`
- `concept.sql`
