Evidence block — Concept `height`, attempt `0001`.

The implementer read `AGENTS.md`, `LOOP_CONTRACT.md`, complete `MIMIC_NOTES.md`, all `MIMIC_NOTES.d` fragments, and both reusable height analyses. It produced:

- `mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0001/ViewDefinition.height_observation.json`
- `mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0001/ViewDefinition.height_patient.json`
- `mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0001/ViewDefinition.height_encounter.json`
- `mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0001/concept.sql`

The port projects Observation Quantity values for itemids 226707 and 226730, joins Patient and ICU Encounter identifier spines, filters by exact system+code, full-outer-joins the two streams on subject and charttime, converts inches to centimetres, rounds, and applies strict `120 < height < 230`. Final columns are explicitly cast as `subject_id INTEGER`, `stay_id INTEGER`, `charttime TIMESTAMP_NTZ`, and `height DECIMAL(38,2)`. No `unrepresentable.json` was needed. No new dataset-wide quirk was established and no notes fragment was modified.
