# Evidence — concept-implementer

Read the contract, curated notes, provisional fragments, canonical height SQL,
source analysis, and fresh FHIR probe. Authored three ViewDefinitions and the
Spark SQL port in this attempt. The port filters the exact chartevents system
and codes, joins numeric identifiers through Patient and ICU Encounter
identifier values, uses served effective dateTime as `TIMESTAMP_NTZ`, preserves
the source full outer join on subject plus charttime, applies centimetre
precedence, inch conversion, rounding, and strict bounds, and emits the
manifest schema. No resource ID construction or inversion is present.

`uv run mimic_utils lint-sql height` passed. No new dataset-wide quirk was
found, so `MIMIC_NOTES.d/height.md` was unchanged.

Artifacts:
- `ViewDefinition.height_observation.json`
- `ViewDefinition.height_patient.json`
- `ViewDefinition.height_encounter.json`
- `concept.sql`
