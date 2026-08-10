Evidence block — concept `acei`, stage `concept-implementer`, attempt 0004.

Read LOOP_CONTRACT.md, MIMIC_NOTES.md, source and refreshed FHIR carryover,
the carryover ledger, and all attempt_0003 evidence/artifacts. Created once:

- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.medication.json`
- `ViewDefinition.medication_mix.json`
- `ViewDefinition.medication_request.json`
- `concept.sql`

The new mix ViewDefinition materializes
`ingredient.itemReference.getReferenceKey(Medication)`. SQL resolves each
component Medication's name identifier, combines direct and medication-mix
branches with `UNION ALL`, and preserves source multiplicity. It retains all
ten ACEI predicates, identifier-to-integer casts, hospital Encounter filtering,
bounded `VARCHAR(255)`, nullable TIMESTAMP_NTZ validity parsing, and no
`authoredOn` substitution. No `unrepresentable.json` is required.

Static JSON, Spark parser, manifest-order/type, demo shape, and attempt_0003
immutability checks passed. Existing MIMIC_NOTES.md guidance was applied; no
new note was added or updated. The immutable artifacts are under
`mimic-iv/concepts_fhir/concepts/medication/acei/attempt_0004/`.
