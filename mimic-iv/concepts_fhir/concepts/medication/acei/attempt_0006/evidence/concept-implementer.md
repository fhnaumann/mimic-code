# Concept implementer evidence — acei attempt 0006

- Read the authoritative loop contract and the relevant curated MIMIC notes,
  including identifier/resource-key rules, prescription medication mix handling,
  omitted validity periods, Spark bounded `VARCHAR` casts, and `TIMESTAMP_NTZ`.
- Read the reusable acei source analysis and FHIR probe carryover, plus the
  provisional `MIMIC_NOTES.d/arb.md` lead without treating it as evidence.
- Applied the reopened-attempt instruction: retained the five oracle columns and
  added the paired resource-key support columns beside the MIMIC identifiers in
  the outermost result.
- Created five ViewDefinitions and `concept.sql`. The SQL has direct and
  medication-mix ingredient `UNION ALL` branches, exact ten ACEI name filters,
  hospital MedicationRequest filtering, validity-period timestamps only, and
  opaque equality joins for resource keys. No resource-id parsing or inversion
  was used, and no `unrepresentable.json` was needed.
- `uv run mimic_utils lint-sql acei` completed cleanly.
- No dataset-wide notes fragment was appended.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/medication/acei/attempt_0006/ViewDefinition.patient.json`
- `mimic-iv/concepts_fhir/concepts/medication/acei/attempt_0006/ViewDefinition.encounter.json`
- `mimic-iv/concepts_fhir/concepts/medication/acei/attempt_0006/ViewDefinition.medication_request.json`
- `mimic-iv/concepts_fhir/concepts/medication/acei/attempt_0006/ViewDefinition.medication.json`
- `mimic-iv/concepts_fhir/concepts/medication/acei/attempt_0006/ViewDefinition.medication_mix.json`
- `mimic-iv/concepts_fhir/concepts/medication/acei/attempt_0006/concept.sql`
