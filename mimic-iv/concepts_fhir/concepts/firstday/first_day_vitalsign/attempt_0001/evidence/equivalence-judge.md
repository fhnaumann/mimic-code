# Equivalence judge evidence

The independent judge read the authoritative `MIMIC_NOTES.md`, target
artifacts/comparison, full attempt history, and the diagnostician's cited
decomposition. It returned `accept` for the contested review.

All 183 conflicts close under proven spring-forward normalization: 176 are
inherited from the completed divergent `vitalsign` dependency through
`mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`, and 7 are direct ICU
anchor effects through `mimic-fhir/sql/fhir_encounter_icu.sql:31,98`. The
candidate reads those normalized FHIR elements, uses opaque-key equality, and
preserves the canonical closed `[intime - 6h, intime + 1d]` window. The source
wall times are absent from FHIR; `Observation.issued` is storetime and resource
IDs are opaque, so no query can recover the originals. The affected fraction
is 183/73,181 (0.2501%), consistent with rare DST events amplified by
chart-time grouping/window aggregation. The dependency's hard-coded omission
is outside this target's window. The contract's explicit DST exemption applies
even though the shifted anchors affect aggregate values and window membership.

Fidelity: 72,998/73,181 identical (99.7499%); no only-oracle, only-candidate,
or null-only rows; no representability declaration. The judge's dataset-wide
finding on ICU Encounter `period.start` was appended to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/first_day_vitalsign.md`.
