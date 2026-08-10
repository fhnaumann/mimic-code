## Concept-implementer evidence

I read the canonical cardiac-marker SQL, both carryover analyses, `MIMIC_NOTES.md`, the cardiac-marker notes fragment, the full oracle manifest, and the FHIR mapping and Pathling SQL conventions. I created the four write-once ViewDefinitions and `concept.sql` in this attempt:

- `ViewDefinition.lab_observation.json`
- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.specimen.json`
- `concept.sql`

The implementation filters the exact lab coding system and active string codes, requires a non-null Quantity value, joins UUID reference keys to identifier values, uses a nullable hospital-Encounter LEFT JOIN, groups by specimen, reproduces the source MAX pivots, and explicitly casts all seven manifest columns. Datetime output uses `TIMESTAMP_NTZ`; no `unrepresentable.json` is needed. JSON labels match filenames and SQL table references. No new dataset-wide note was identified or appended.

Result: implementation artifacts are complete and frozen for the demo shape gate.
