Evidence block

Concept: `cardiac_marker`; attempt: `0005`.

Created:
- `ViewDefinition.lab_observation.json`
- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.specimen.json`
- `concept.sql`

The implementation projects Observation, Patient, hospital Encounter, and Specimen keys; filters the exact lab system and string codes; excludes nonnumeric/comparator quantities; uses opaque-key joins, a left Encounter join, specimen grouping, explicit manifest casts, and prefixed resource-key outputs. No `unrepresentable.json` was needed.

Applied shared notes on opaque resource keys, identifier strings, lab specimen grouping, incomplete lab encounters, Quantity casting, polymorphic choices, and `TIMESTAMP_NTZ` datetime handling. Read all existing `MIMIC_NOTES.d/*.md` fragments, treating them as provisional; relevant lab fragments were cross-checked against the supplied `fhir-prober` analysis. No fragment was appended.

Validation completed:
- JSON parsing: passed.
- `uv run mimic_utils lint-sql cardiac_marker`: clean.

Artifacts: `mimic-iv/concepts_fhir/concepts/measurement/cardiac_marker/attempt_0005/ViewDefinition.lab_observation.json`, `ViewDefinition.patient.json`, `ViewDefinition.encounter.json`, `ViewDefinition.specimen.json`, and `concept.sql`.
