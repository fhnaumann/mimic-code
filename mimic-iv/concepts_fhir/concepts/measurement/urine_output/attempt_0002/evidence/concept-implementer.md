# Concept implementer evidence

Concept: `urine_output`; attempt `0002`.

Fresh artifacts created:
- `ViewDefinition.urine_output_observation.json`
- `ViewDefinition.urine_output_encounter.json`
- `concept.sql`

The implementation preserves the validated attempt-0001 semantics: Observation Quantity/dateTime projection, exact twelve `mimic-d-items` codes, opaque Encounter-reference equality join, ICU `stay_id` from `identifier.value`, positive `227488` negation, `DOUBLE` Quantity conversion, `TIMESTAMP_NTZ` charttime, and grouping by `(stay_id, charttime)`. All manifest columns are explicitly cast. No IDs are parsed or emitted and no `unrepresentable.json` is needed.

The comparator provenance defect from attempt 0001 was corrected separately in `src/mimic_utils/compare_port_results.py` by adding `mimic-fhir/sql/fhir_observation_outputevents.sql:9,60,62-65`; this attempt does not alter candidate semantics. `uv run mimic_utils lint-sql urine_output` passed cleanly. No state transitions or commit were performed.
