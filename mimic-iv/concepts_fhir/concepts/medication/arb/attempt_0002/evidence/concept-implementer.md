# Concept implementer evidence

Retry attempt 0002 was authored from reusable `carryover/arb/source-analyst.md` and `carryover/arb/fhir-prober.md`, with attempt 0001 inspected but not modified. Read `LOOP_CONTRACT.md` and `MIMIC_NOTES.md`.

Created once under this attempt: `ViewDefinition.medication_request.json`, `ViewDefinition.medication.json`, `ViewDefinition.medication_mix.json`, `ViewDefinition.patient.json`, `ViewDefinition.encounter.json`, and `concept.sql`. The port preserves direct and mix ingredient branches, exact ARB filters, identifier-based integer casts, bounded `VARCHAR(255)`, nullable `TIMESTAMP_NTZ` parsing, and NULL validity periods where FHIR omits them. No unrepresentable declaration or shared-note update was needed.
