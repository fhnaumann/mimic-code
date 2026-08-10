# Evidence: concept-implementer (`bg`, attempt_0005)

Read `AGENTS.md`, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, the canonical
`mimic-iv/concepts/measurement/bg.sql`, both reusable `bg` carryover analyses,
the attempt 0004 artifacts/evidence, and its mismatch diagnosis.

Created in the new immutable attempt:

- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.specimen.json`
- `ViewDefinition.lab_observation.json`
- `ViewDefinition.chart_observation.json`
- `concept.sql`

The exact fix is `CAST(specimen AS VARCHAR(255))` instead of the Spark-invalid
bare `VARCHAR` cast. All other semantics are preserved: five-resource
projections, specimen grouping, exact lab/chart code systems, left Encounter
join, identifier and Quantity casts, `TIMESTAMP_NTZ`, chart windows and
row-number logic, FLOAT chart FiO2, DECIMAL(38,4) AADO2, and all 27 manifest
columns. No key or `unrepresentable.json` was added.

Static JSON, label/name, Spark SQL parsing, manifest-order/type, and attempt-diff
checks passed. No HPC run or commit was performed. `MIMIC_NOTES.md` was read;
no entry was added or updated.

Artifacts: `mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0005/`.
