# Concept implementer evidence

Implemented reopened attempt 0003 from the reusable `carryover/arb/source-analyst.md` and `carryover/arb/fhir-prober.md`, reading `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, all notes fragments, prior attempt 0002 artifacts/evidence, and the canonical ViewDefinition conventions. Created once: `ViewDefinition.medication_request.json`, `ViewDefinition.medication.json`, `ViewDefinition.medication_mix.json`, `ViewDefinition.patient.json`, `ViewDefinition.encounter.json`, and `concept.sql`.

The port preserves direct and medication-mix ingredient `UNION ALL` branches, all 16 literal ARB filters, identifier-based integer casts, bounded `VARCHAR(255)`, and NULL validity periods omitted by upstream FHIR. Replaced the prior format-specific datetime parser with direct `TRY_CAST(starttime_str AS TIMESTAMP_NTZ)` and `TRY_CAST(stoptime_str AS TIMESTAMP_NTZ)` as required by the reopen reason. JSON parsing and static forbidden-parser checks passed. No dataset-wide quirk was discovered and `MIMIC_NOTES.d/arb.md` was not modified; existing notes already cover identifier spines, medication-name identifiers, omitted validity periods, and TIMESTAMP_NTZ handling.

Artifacts: `mimic-iv/concepts_fhir/concepts/medication/arb/attempt_0003/ViewDefinition.*.json` and `mimic-iv/concepts_fhir/concepts/medication/arb/attempt_0003/concept.sql`.
