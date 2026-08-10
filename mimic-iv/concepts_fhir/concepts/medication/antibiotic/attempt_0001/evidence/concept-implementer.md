Evidence block:

- Read the canonical antibiotic SQL, source and FHIR carryovers, LOOP_CONTRACT.md, AGENTS.md, and MIMIC_NOTES.md.
- Wrote seven-column implementation artifacts under this attempt: `ViewDefinition.medication.json`, `ViewDefinition.medication_mix.json`, `ViewDefinition.medication_request.json`, `ViewDefinition.patient.json`, `ViewDefinition.encounter.json`, `ViewDefinition.encounter_icu.json`, and `concept.sql`.
- The SQL uses direct and medication-mix ingredient branches with `UNION ALL`, preserves ingredient multiplicity and source name/route predicates, filters the route coding system, joins patient and hospital Encounter identifiers, assigns ICU stays through `Encounter.partOf` and a half-open temporal interval, and casts output columns to the manifest schema.
- `drug_type` is a non-output source filter absent from FHIR; no heuristic or `unrepresentable.json` was used because the oracle does not contain that internal filter flag as an output column.
- No new dataset-wide note was needed; existing shared notes were read and applied. Implementation artifacts are write-once and no commit was made.
