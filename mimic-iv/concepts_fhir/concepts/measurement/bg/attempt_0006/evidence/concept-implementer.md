# Evidence: concept-implementer (`bg`, attempt_0006)

Read the authoritative loop documents, `MIMIC_NOTES.md`, canonical bg SQL,
reusable source/FHIR carryovers, and attempt 0005's full divergence diagnosis.
Reused both carryover analyses unchanged.

Created fresh implementation artifacts:

- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.specimen.json`
- `ViewDefinition.lab_observation.json`
- `ViewDefinition.chart_observation.json`
- `concept.sql`

Required corrections are present: `CAST(specimen AS VARCHAR(255)) AS specimen`
and outer `CAST(charttime AS TIMESTAMP_NTZ) AS charttime`; internal datetime
casts remain `TIMESTAMP_NTZ`. Specimen grouping, proprietary systems/itemids,
left Encounter join, identifier/Quantity casts, `NULLIF(value_string, '___')`,
source pivots, chart windows/row numbers, FLOAT FiO2, DECIMAL(38,4) AADO2, and
all 27 manifest columns are preserved. No key or unrepresentable declaration
was added.

Static JSON, manifest order/type, label/name, artifact-count, and attempt-delta
checks passed. No HPC run or commit was performed. `MIMIC_NOTES.md` was read;
no entry was added or updated.

Artifacts: `mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0006/`.
