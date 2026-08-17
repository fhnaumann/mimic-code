# Evidence: concept-implementer

## Read and checked

The implementation used the canonical `demographics/age.sql`, the current
source and FHIR-prober carryover, `LOOP_CONTRACT.md`, curated MIMIC notes, and
the ViewDefinition/Pathling SQL conventions. The reopened instruction was
applied verbatim: resource keys are emitted additively beside the compared
identifier columns, and `Encounter.getResourceKey()` is projected.

## Artifacts authored

- `ViewDefinition.encounter.json`: hospital Encounter identifier filter,
  `encounter_key`, `patient_key`, `hadm_id_str`, and `period_start`.
- `ViewDefinition.patient.json`: `patient_key`, patient identifier
  `subject_id_str`, and `birth_date`.
- `concept.sql`: joins `encounter` to `patient` on opaque Patient key,
  casts identifier strings to INTEGER, casts dateTime to `TIMESTAMP_NTZ`,
  derives age from year subtraction, emits `patient_key` and `encounter_key`,
  and preserves the manifest's six compared columns.
- `unrepresentable.json`: declares `anchor_age` and `anchor_year` absent from
  FHIR and emitted as typed `CAST(NULL AS SMALLINT)` rather than estimates.

`uv run mimic_utils lint-sql age` passed. A manual manifest/shape audit found
the compared names and types and both required resource-key columns. No demo
execution was run by this stage, and no new dataset-wide fragment was added.

## Artifacts

All implementation artifacts are in
`mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0003/`.
