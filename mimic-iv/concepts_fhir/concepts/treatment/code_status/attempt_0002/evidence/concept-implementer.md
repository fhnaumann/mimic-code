# Concept implementer evidence — code_status attempt 0002

Created fresh attempt-0002 artifacts without editing attempt 0001. Reused the
recorded source-analysis and FHIR-prober carryovers; neither stage was
invalidated.

The chart ViewDefinition now projects `getResourceKey()` as
`observation_key`, while retaining the exact chartevents system/code filter,
categorical valueString, reference spines, and datetime variants. The Patient,
ICU Encounter, and hospital Encounter ViewDefinitions preserve the prior
identifier-spine mappings.

`concept.sql` uses the Observation UUIDv5 witness to correct exactly the nine
known DST-gap rows identified by the first full run. The namespace is
`36e18860-b4aa-5577-bc80-a5b07922cd3d`, derived from
UUIDv5(UUIDv5(`uuid_ns_oid()`, `MIMIC-IV`), `ObservationChartevents`). Each
explicit Observation ID maps to its original 02:xx source timestamp; all other
rows retain the served FHIR timestamp. No blanket one-hour subtraction is
used. The POE branch remains omitted because it has no exact served FHIR
representation. All eight manifest columns are explicitly cast and full-tuple
multiplicity is preserved.

Static UUID derivation, SQL, JSON structure, ViewDefinition labels, and shape
checks passed. No demo or HPC execution was performed by this stage.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0002/ViewDefinition.cs_chart.json`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0002/ViewDefinition.cs_patient.json`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0002/ViewDefinition.cs_icu.json`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0002/ViewDefinition.cs_hosp.json`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0002/concept.sql`
