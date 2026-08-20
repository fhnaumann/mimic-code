# FHIR-prober evidence — `first_day_rrt`

Read `MIMIC_NOTES.md`, the source analysis, the completed `rrt` attempt and
carryover, and relevant sibling fragments (`first_day_bg.md`, `rrt.md`,
`crrt.md`, `icustay_times.md`, and `icustay_detail.md`) as provisional leads.
Probed the authoritative demo Delta with embedded Pathling 9.6.0/Spark 4.0.2.

The ICU stay population maps to `Encounter` filtered by
`identifier.system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'`.
`stay_id` comes from the encounter identifier value and `subject_id` from the
referenced Patient identifier; both are strings in FHIR and require final
integer casts. Required opaque identity outputs are `getResourceKey()` as
`icu_encounter_key` and `subject.getReferenceKey(Patient)` as `patient_key`;
they are used only for equality joins and must be emitted verbatim. ICU
`intime` maps to `Encounter.period.start`, which materializes as a string and
must be cast directly to `TIMESTAMP_NTZ`.

The completed dependency is consumed from the preprocessed `rrt` temp view,
joining on its published `icu_encounter_key`; raw RRT FHIR rederivation is
forbidden. The dependency carries `charttime`, the two flags, and nullable
`dialysis_type`. The target preserves all 140 ICU stays with a LEFT JOIN over
the inclusive `[-6 hours, +1 day]` window and aggregates to the manifest's
five compared columns. Demo probes found all 140 ICU identities, patient
references, and period starts populated; the reconstructed aggregation agreed
with the DuckDB oracle on 140/140 rows. No new dataset-wide quirk was
established and no fragment was appended.

Reusable mapping was written to
`mimic-iv/concepts_fhir/carryover/first_day_rrt/fhir-prober.md` and recorded
with `mimic_utils carryover-record`.
