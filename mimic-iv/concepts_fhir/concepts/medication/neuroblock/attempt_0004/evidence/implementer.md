# Implementer evidence — neuroblock attempt 0004

The implementer read the canonical source, reusable neuroblock carryover,
oracle manifest, curated notes, reopened resource-key instruction, and
relevant ICU medication fragments. It authored fresh ViewDefinitions,
`concept.sql`, and `unrepresentable.json` with exact medication codes and
typed-NULL orderid.

The initial implementation retained `icu_encounter_key` but omitted the
manifest-required additive `patient_key`. The implementer reported that
`uv run mimic_utils lint-sql neuroblock` rejected the missing key. The
orchestrator failed this attempt as an engineering/shape issue and created
attempt 0005 under the write-once contract; no demo or full run was spent on
attempt 0004 and no files in it were edited.
