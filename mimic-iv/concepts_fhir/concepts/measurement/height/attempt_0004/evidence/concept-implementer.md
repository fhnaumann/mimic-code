# Concept-implementer evidence

The implementer read the source and FHIR carryovers, the curated
`MIMIC_NOTES.md`, and the reopened instruction. It authored three canonical
ViewDefinitions and `concept.sql` in attempt 0004. The implementation uses
exact itemids `226707` and `226730`, ICU identifier filtering, opaque resource
keys only for equality joins/output key columns, direct `TIMESTAMP_NTZ`
handling, centimetre precedence, the source full outer join on subject and
charttime, conversions, rounding, and strict bounds. It added the required
`patient_key` and `icu_encounter_key` columns beside the compared identifiers.

`uv run mimic_utils lint-sql height` passed. No dataset-wide note was appended;
the relevant effective-choice, identifier, Quantity, datetime, and opaque-id
rules were already curated or verified in the carryover.

Artifacts produced once:

- `mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0004/ViewDefinition.height_observation.json`
- `mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0004/ViewDefinition.height_patient.json`
- `mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0004/ViewDefinition.height_encounter.json`
- `mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0004/concept.sql`
