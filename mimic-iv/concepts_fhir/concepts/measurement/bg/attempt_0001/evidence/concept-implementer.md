# Concept-implementer evidence — bg

**Attempt:** `measurement/bg/attempt_0001`.

Created the following write-once artifacts:

- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.specimen.json`
- `ViewDefinition.lab_observation.json`
- `ViewDefinition.chart_observation.json`
- `concept.sql`

No `unrepresentable.json` was needed: all 27 manifest columns have FHIR
representations. The implementation projects Patient, hospital Encounter,
Specimen, laboratory Observation, and ICU chart Observation data; joins UUID
references; links specimens; left-joins hospital Encounter IDs; filters exact
proprietary systems/codes; applies plausibility rules and 2/4-hour SpO2/FiO2
windows; and emits explicit outer casts including `TIMESTAMP_NTZ`, `FLOAT`, and
`DECIMAL(38,4)`.

Static JSON/label validation, Spark SQL parsing, label-only source validation,
and manifest/schema verification passed. Demo execution was not run at this
stage. Existing applicable `MIMIC_NOTES.md` entries were used; no new entry
was reported by the implementer.

**Remaining risk:** full-data FHIR coverage differences and the required
unkeyed full-tuple multiset comparison remain to be evaluated on HPC.
