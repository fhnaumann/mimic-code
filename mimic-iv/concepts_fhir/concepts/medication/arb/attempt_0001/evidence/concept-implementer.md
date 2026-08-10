# Concept implementer evidence

Read the contract, `MIMIC_NOTES.md`, the source analysis, the FHIR probe, the full oracle manifest, and prior medication-port patterns. Created the following immutable attempt artifacts:

- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.medication_request.json`
- `ViewDefinition.medication.json`
- `ViewDefinition.medication_mix.json`
- `concept.sql`

The implementation projects identifier values rather than UUID resource keys, handles direct and medication-mix ingredient references with `UNION ALL`, preserves the 16 case-insensitive source substring filters and DISTINCT semantics, uses bounded Spark `VARCHAR` casts and nullable `TIMESTAMP_NTZ` parsing, and leaves omitted invalid/incomplete FHIR validity periods as NULL. The manifest is unkeyed and the implementation targets full-tuple comparison. No `unrepresentable.json` is needed. Existing shared notes were read and applied; no new note was added or modified.
