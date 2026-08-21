# Concept implementer evidence — icustay_hourly

Read the canonical SQL, source/FHIR carryover analyses, oracle manifest,
completed `icustay_times` attempt, `AGENTS.md`, the FHIR mapping and
Pathling-SQL conventions, `MIMIC_NOTES.md`, and the provisional fragments.

Authored the ICU Encounter ViewDefinition and candidate SQL. The SQL consumes
the published `icustay_times` view, joins the opaque ICU Encounter key, reads
`stay_id` only from the exact ICU Encounter identifier system, generates the
inclusive `-24` through HOUR-boundary offset range, and preserves
`TIMESTAMP_NTZ` wall-clock semantics. It emits `stay_id`, `hr`, `endtime`,
`icu_encounter_key`, and `patient_key`.

`uv run mimic_utils lint-sql icustay_hourly` was clean. No unrepresentable
declaration was required and no new notes fragment entry was appended.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/demographics/icustay_hourly/attempt_0001/ViewDefinition.icustay_hourly_icu_encounter.json`
- `mimic-iv/concepts_fhir/concepts/demographics/icustay_hourly/attempt_0001/concept.sql`
