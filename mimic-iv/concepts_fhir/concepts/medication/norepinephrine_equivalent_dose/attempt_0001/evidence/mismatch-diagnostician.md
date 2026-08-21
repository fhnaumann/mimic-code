# Demo mismatch diagnosis

The failure occurred before SQL execution because `demo_runner` requires at
least one `ViewDefinition.*.json`. The attempt also incorrectly selected
`v.stay_id` from the published `vasoactive_agent` dependency. Publication
strips identifier columns when the dependency carries its opaque
`icu_encounter_key`, so a dummy compatibility ViewDefinition would only expose
the next failure.

This is a fixable engineering/shape bug, not semantic rework and not a runner
defect. A fresh attempt must add a real `ViewDefinition.encounter_icu.json`
with label/name `encounter_icu`, projecting `getResourceKey()`, the patient
reference key, and the ICU Encounter identifier value. Fresh SQL must cast that
identifier to `INTEGER`, join it to `vasoactive_agent.icu_encounter_key`, and
retain the canonical five-rate filter/formula. It must not collide with the
dependency label or use any resource-id inversion.

The diagnosis invalidates reusable `fhir-prober` carryover because its
published-shape assumption was wrong; `source-analyst` remains reusable. No
new dataset-wide quirk was found and no notes fragment was appended.

Paths read included the attempt artifacts, canonical SQL, manifest, completed
dependency attempt, runner/export code, and curated notes. No files were edited
by the diagnostician.
