# Evidence: concept-implementer (`bg`, attempt_0004)

Read `AGENTS.md`, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, the canonical
`mimic-iv/concepts/measurement/bg.sql`, and the reusable `bg` source-analysis
and FHIR-prober carryover files.

Created the implementation artifacts:

- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.specimen.json`
- `ViewDefinition.lab_observation.json`
- `ViewDefinition.chart_observation.json`
- `concept.sql`

The port preserves the 27 manifest columns and required types, the specimen
grouping spine, exact lab/chart code-system filters, left hospital Encounter
join, numeric identifier and Quantity casts, `TIMESTAMP_NTZ` datetime handling,
the `NULLIF(value_string, '___')` correction, source pivot constraints,
2-hour/4-hour chart windows, row-number selection, FLOAT chart FiO2, and
DECIMAL(38,4) AADO2 calculation. No unrepresentable declaration was needed.

Static checks passed: JSON syntax and ViewDefinition label/name validation,
Spark SQL parsing with sqlglot 30.15.0, manifest column order/type validation,
and required joins, filters, casts, and output types. Demo and full gates were
not run at this stage.

`MIMIC_NOTES.md` was read; no new dataset-wide entry was added or updated.

Artifacts: `mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0004/`.
