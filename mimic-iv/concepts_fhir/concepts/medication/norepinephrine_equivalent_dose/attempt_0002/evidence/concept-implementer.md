# Concept implementer evidence

The implementer authored a real `ViewDefinition.encounter_icu.json` with
label/name `encounter_icu`, projecting opaque Encounter/Patient keys and the
ICU Encounter identifier system/value. Fresh `concept.sql` joins the published
`vasoactive_agent.icu_encounter_key` to `encounter_icu.encounter_key`, recovers
`stay_id` from the identifier value, preserves duplicates, applies the exact
five-rate filter/formula, and emits manifest-compatible ordinary columns plus
verbatim opaque support keys.

`uv run mimic_utils lint-sql norepinephrine_equivalent_dose` passed cleanly.
No unrepresentable declaration or notes fragment entry was needed.

Artifacts: `ViewDefinition.encounter_icu.json` and `concept.sql` in attempt_0002.
