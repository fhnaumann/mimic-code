Concept `sepsis3`; FHIR-probing stage for attempt_0001.

Read the source analysis, `AGENTS.md`, `MIMIC_NOTES.md`, canonical SQLs,
oracle manifest, canonical ViewDefinition reference, and provisional fragments
`sofa.md`, `suspicion_of_infection.md`, `icustay_detail.md`, `icustay_times.md`,
and `README.md`. Provisional fragment claims were verified against the
authoritative demo Delta warehouse with embedded Pathling 9.6.0 / Spark 4.0.2.

The target must consume completed dependency views as unqualified `sofa` and
`suspicion_of_infection`, never rederive them from raw FHIR. Opaque equality
joins are `soi.icu_encounter_key = sofa.icu_encounter_key`; source integer
identifiers are recovered from ICU `Encounter.identifier` and Patient
`identifier.value`, then cast only for output. The ICU stream is selected by
`identifier.system =
http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`. The source inclusive
time window is `sofa.endtime` from 48 hours before through 24 hours after
`suspected_infection_time`; retain `ROW_NUMBER()` 1 per ICU encounter ordered by
the four source fields. The Boolean remains `sofa_score >= 2 AND
suspected_infection = 1`.

Canonical support mappings verified include `getResourceKey()` for
`icu_encounter_key`, `subject.getReferenceKey(Patient)` for `patient_key`, ICU
identifier values for `stay_id`, and the dependency's published timestamp and
score/component columns. The oracle manifest requires 14 output columns, a
keyed join on `stay_id`, required FHIR comparison keys `icu_encounter_key` and
`patient_key`, and 32,971 full-oracle rows. Demo probes found 12,255 `sofa`
rows and 903 suspicion rows; ICU Encounter and Patient identifier/key coverage
was complete on the demo stream.

Inherited dependency losses were recorded as leads for the eventual full
comparison: invalid/incomplete MedicationRequest validity periods affect
suspicion times and ICU assignment, and accepted SOFA precision/encoder loss
may affect the target's threshold/selection. The target must consume those
dependency outputs unchanged; no estimate or resource-id inversion is allowed.

The probe appended this dataset/IG-level entry to the owned fragment:
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/sepsis3.md` — ICU Encounter
`period.start`/`period.end` are populated 140/140 on the ICU stream, verified
with embedded Pathling. No other dataset-wide quirk was reported.

Reusable artifacts:
- `mimic-iv/concepts_fhir/carryover/sepsis3/fhir-prober.md`
- `mimic-iv/concepts_fhir/carryover/sepsis3/carryover.json`
- `mimic-iv/concepts_fhir/MIMIC_NOTES.d/sepsis3.md`
