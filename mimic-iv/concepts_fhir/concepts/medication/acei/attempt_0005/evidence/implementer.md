# Implementer evidence — `acei`, attempt `0005`

Read the reusable source analysis and FHIR probe, the curated MIMIC notes and
fragments, the oracle manifest, source SQL, and prior attempt evidence.

Created five ViewDefinitions (`patient`, `encounter`, `medication_request`,
`medication`, and `medication_mix`) plus `concept.sql`. The implementation
uses the identifier spines, direct and medication-mix ingredient branches with
`UNION ALL`, exact ten ACEI substring predicates, duplicate preservation,
bounded Spark VARCHAR casts, and `TIMESTAMP_NTZ` parsing. Invalid or incomplete
validity periods remain typed NULLs from the absent FHIR elements. No new
dataset-wide quirk was discovered, so `MIMIC_NOTES.d/acei.md` was unchanged.

Artifacts:
- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.medication_request.json`
- `ViewDefinition.medication.json`
- `ViewDefinition.medication_mix.json`
- `concept.sql`
