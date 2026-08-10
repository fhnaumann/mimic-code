# Concept implementer evidence — code_status attempt 0001

Implemented the representable ICU chart-event branch for `code_status`.

ViewDefinitions created:
- `ViewDefinition.cs_chart.json` — `Observation`, exact chartevents system
  and code `223758`, categorical `value.ofType(string)`, subject and ICU
  encounter reference keys, and both datetime choice variants.
- `ViewDefinition.cs_patient.json` — Patient UUID join key and patient
  identifier value.
- `ViewDefinition.cs_icu.json` — ICU Encounter UUID, patient reference,
  ICU identifier, parent hospital reference, and period bounds.
- `ViewDefinition.cs_hosp.json` — hospital Encounter UUID and hospital
  identifier value.

`concept.sql` joins only those materialized labels, preserves chart-event
multiplicity, filters by system plus exact code, uses `TIMESTAMP_NTZ` for
`charttime`, and explicitly casts all eight manifest columns:
`subject_id`, `hadm_id`, `stay_id`, `charttime`, `fullcode`, `cmo`, `dni`, and
`dnr`. The absent POE code-status branch is intentionally not mapped to an
unrelated MedicationRequest resource; its rows remain a coverage gap for the
full-data comparator. No natural key or unrepresentable-column declaration was
invented.

Static JSON, ViewDefinition label/name, structure, manifest shape, and SQL
token checks passed. Demo execution was not run by this stage. No new
dataset-wide quirk was discovered or appended to `MIMIC_NOTES.d/code_status.md`.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0001/ViewDefinition.cs_chart.json`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0001/ViewDefinition.cs_patient.json`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0001/ViewDefinition.cs_icu.json`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0001/ViewDefinition.cs_hosp.json`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0001/concept.sql`
