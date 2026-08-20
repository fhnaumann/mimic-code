# Implementer evidence

Concept: `antibiotic`, attempt 0003.

Artifacts authored once:

- `ViewDefinition.medication_request.json`
- `ViewDefinition.medication.json`
- `ViewDefinition.medication_mix.json`
- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.encounter_icu.json`
- `concept.sql`

The implementation uses direct and medication-mix ingredient branches with
`UNION ALL`, preserves multiplicity, applies the source antibiotic substring
and route predicates, uses identifier spines and paired resource keys, bounded
`VARCHAR(255)`, and `TRY_CAST(... AS TIMESTAMP_NTZ)`. `drug_type` is not
represented by FHIR and no estimate was substituted; no declaration was
needed. Resource ids remain opaque join identity only.

Read: `AGENTS.md`, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, both antibiotic
carryover analyses, prior attempts, `TODO_reopen_resource_keys.md`, and the
provisional `MIMIC_NOTES.d/arb.md` lead, which was cross-checked against the
antibiotic evidence.

Validation: `uv run mimic_utils lint-sql antibiotic` passed cleanly. No new
dataset-wide quirk was discovered and no notes fragment was appended.
