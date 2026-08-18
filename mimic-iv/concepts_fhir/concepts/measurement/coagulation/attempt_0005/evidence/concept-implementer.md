# Concept implementer evidence — coagulation attempt 0005

Read `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, the coagulation source-analyst and
FHIR-prober carryover, relevant dataset fragments, the oracle manifest, the
canonical ViewDefinition example, and the reopened-attempt instruction about
retaining paired resource-key columns.

Created fresh implementation artifacts:

- `ViewDefinition.lab_observation.json`
- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.specimen.json`
- `concept.sql`

The implementation preserves the six literal lab itemids, the labevents
numeric-value/comparator safeguards, left-sided encounter join, specimen
grouping, independent `MAX` pivots, `TIMESTAMP_NTZ` datetime handling, and
paired resource-key outputs. JSON validation and
`uv run mimic_utils lint-sql coagulation` passed. No new dataset-wide note was
identified or appended.

Artifacts are under:
`mimic-iv/concepts_fhir/concepts/measurement/coagulation/attempt_0005/`.
