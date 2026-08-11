# Implementer evidence — complete_blood_count, attempt_0002

Read the canonical source SQL, oracle manifest, curated MIMIC_NOTES.md, relevant
MIMIC_NOTES.d fragments, and reusable source-analyst/fhir-prober carryover.
Checked that the exact ten itemids, lab coding system, positive numeric filter,
specimen grouping, nullable hospital Encounter join, identifier casts, and
wall-clock datetime handling were represented.

Static JSON parsing and structure checks passed. Created the four support and
observation ViewDefinitions plus concept.sql. The SQL projects all 14 manifest
columns in order with explicit compatible casts. No unrepresentable declaration
was needed and no new dataset-wide notes entry was added.

Artifacts:
- ViewDefinition.lab_observation.json
- ViewDefinition.patient.json
- ViewDefinition.specimen.json
- ViewDefinition.encounter.json
- concept.sql
