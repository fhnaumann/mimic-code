# Concept-implementer evidence

Read the source and FHIR-prober carryover, loop contract, AGENTS.md, curated and dobutamine notes, and relevant medication guidance. Created `ViewDefinition.medication_administration.json` for ICU MedicationAdministration filtered by the exact MIMIC medication system/code, `ViewDefinition.encounter_icu.json` for the ICU Encounter identifier spine, `concept.sql` with explicit manifest casts, LEFT JOIN row preservation, effective choice handling, and typed NULL `linkorderid`, plus `unrepresentable.json` declaring the absent linkorderid representation. JSON, label/name, manifest schema/order, required predicates/casts, and whitespace checks passed. No existing artifact was edited and no commit was made.

Artifacts: `mimic-iv/concepts_fhir/concepts/medication/dobutamine/attempt_0001/ViewDefinition.medication_administration.json`, `ViewDefinition.encounter_icu.json`, `concept.sql`, and `unrepresentable.json`.
