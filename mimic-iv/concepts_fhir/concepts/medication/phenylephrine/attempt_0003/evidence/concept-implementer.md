# Concept implementer evidence

- Concept: `phenylephrine`
- Attempt: `0003`
- Read: the reused source analysis and FHIR mapping carryover, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, and the relevant provisional ICU medication fragments.
- Checked: exact ICU medication coding system/code `mimic-medication-icu`/`221749`; opaque ICU Encounter resource-key join; typed output casts; both effective[x] variants; row-level NULL for the unavailable `mcg/min` patient-weight branch; and the reopened requirement to retain `icu_encounter_key` beside `stay_id`.
- Result: created the two ViewDefinitions, `concept.sql`, and `unrepresentable.json` in this attempt. `linkorderid` is declared 100% unrepresentable and emitted as typed `INTEGER` NULL; `vaso_rate` is not declared unrepresentable because only the identifiable `mcg/min` rows are NULLed.
- Verification: `uv run mimic_utils lint-sql phenylephrine` passed; JSON validation and `git diff --check` passed.
- Dataset-wide notes: no new quirk appended; canonical `MIMIC_NOTES.md` was not modified.
- Artifacts: `ViewDefinition.medication_administration.json`, `ViewDefinition.encounter_icu.json`, `concept.sql`, `unrepresentable.json`.
