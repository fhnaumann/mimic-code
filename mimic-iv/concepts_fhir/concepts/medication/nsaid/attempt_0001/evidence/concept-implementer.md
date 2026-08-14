# Evidence — concept-implementer

Concept `nsaid`, attempt `0001`.

Read the source and FHIR carryover analyses, canonical SQL, curated notes,
relevant fragments, and ViewDefinition/Pathling conventions. Authored five
ViewDefinitions and `concept.sql` with direct and medication-mix `UNION ALL`
branches, all 20 exact predicates, identifier joins, bounded VARCHAR output,
and `TRY_CAST(... AS TIMESTAMP_NTZ)` datetime output. Resource IDs are used only
for equality joins. `uv run mimic_utils lint-sql nsaid` passed. No
`unrepresentable.json` was authored and no new dataset-wide note was found.

Artifacts: `ViewDefinition.medication_request.json`,
`ViewDefinition.medication.json`, `ViewDefinition.medication_mix.json`,
`ViewDefinition.patient.json`, `ViewDefinition.encounter.json`, and
`concept.sql` in this attempt directory.
