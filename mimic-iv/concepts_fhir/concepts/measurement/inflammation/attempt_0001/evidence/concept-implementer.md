# Concept implementer evidence

Concept `inflammation`, attempt `0001`.

Created the four resource projections and derived query:

- `ViewDefinition.lab_observation.json`
- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.specimen.json`
- `concept.sql`

The implementation filters exact item code `50889`, positive non-null Quantity
values, excludes comparator/string fallbacks, groups by specimen identifier,
uses left joins for identifier spines, explicitly casts manifest outputs, and
keeps datetime parsing in `TIMESTAMP_NTZ`. No unrepresentable declaration was
needed and no new dataset-wide note was identified. `uv run mimic_utils
lint-sql inflammation` passed.
