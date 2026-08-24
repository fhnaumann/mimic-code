# Mismatch-diagnostician evidence — creatinine_baseline attempt 0003

- Root cause: the candidate referenced removed dependency columns
  `ag.subject_id` and `ag.hadm_id`; the published `age` view exposes
  `patient_key` and `encounter_key` instead.
- Fix required in a new attempt: join `age` to `patient` by opaque
  `patient_key`, join to hospital `encounter` by opaque `encounter_key`, and
  recover numeric `hadm_id` from the hospital Encounter identifier value.
- The manifest requires the seven comparison columns plus candidate-only
  `encounter_key` and `patient_key`; these keys are validated separately and
  excluded from value comparison. They must not be removed.
- This is a fixable implementation/shape bug. No carryover stage is implicated;
  no carryover invalidation is needed.
- Relevant provisional fragments `MIMIC_NOTES.d/age.md` and
  `MIMIC_NOTES.d/creatinine_baseline.md` were checked and are unrelated to the
  failure. No dataset-wide quirk was discovered or appended.
