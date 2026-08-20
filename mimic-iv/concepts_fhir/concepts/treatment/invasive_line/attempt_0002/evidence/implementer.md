# Implementer evidence — invasive_line attempt_0002

- Read the canonical SQL, reusable source analysis and FHIR mapping, the
  authoritative loop contract, `MIMIC_NOTES.md`, and relevant provisional
  fragments including `invasive_line.md`, `icustay_detail.md`,
  `icustay_times.md`, `oxygen_delivery.md`, `dobutamine.md`, and
  `phenylephrine.md`.
- Authored the Procedure and ICU Encounter ViewDefinitions and `concept.sql`
  in this attempt. The port filters the exact 24 itemids and coding system,
  preserves Procedure row multiplicity with `forEachOrNull`, joins ICU
  Encounter by opaque reference key, applies the source CASE mappings, and
  uses `TIMESTAMP_NTZ` casts.
- The reopened resource-key instruction is implemented: the output retains
  the manifest columns and exposes the paired opaque `icu_encounter_key` and
  `patient_key` columns without parsing or reconstructing ids.
- `uv run mimic_utils lint-sql invasive_line` passed. Demo/full validation was
  not run by this stage; attempt_0001 was not modified and no notes fragment
  entry was appended.

Artifacts:

- `ViewDefinition.invasive_line_procedure.json`
- `ViewDefinition.invasive_line_icu_encounter.json`
- `concept.sql`
