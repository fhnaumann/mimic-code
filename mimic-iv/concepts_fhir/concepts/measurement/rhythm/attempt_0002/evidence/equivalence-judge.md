# Equivalence-judge evidence — rhythm attempt 0002

The independent judge returned **accept** for the corrected attributed review.
It cited `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`, which casts
`ce.charttime` through `TIMESTAMPTZ` and writes the normalized value to
`Observation.effectiveDateTime`, the exact element projected by the port.
The full replay accounted for every divergence: 95 differing conflicts, 645
oracle-only rows, and 42 candidate-only rows, with 603 key collisions, 42
repaired pairings, and zero residuals. The 645 uniquely shifted events are
about 0.0110% of 5,873,723 oracle rows, consistent with DST-gap rarity.

The judge confirmed canonical `rhythm.sql` and candidate grouping both use
`(subject_id, charttime)` with ordered distinct `STRING_AGG` and lexical `MAX`,
so collisions are faithful over transformed FHIR data. It confirmed resource
IDs were used only for equality joins and never parsed or regenerated. No
divergent dependencies exist. Fidelity is 5,872,983/5,873,723 identical
(99.9874%), with no unrepresentable columns. The judge read
`LOOP_CONTRACT.md`, curated `MIMIC_NOTES.md`, canonical SQL, attempt_0002
artifacts, and full comparison metadata; it modified no files.
