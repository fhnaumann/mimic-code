# Equivalence judge evidence

The judge returned `accept` for attempt `0002`, tier `attributed`.

The corrected citation `mimic-fhir/sql/fhir_observation_labevents.sql:15,121`
casts `labevents.charttime` through `TIMESTAMPTZ` and writes the transformed
value to `Observation.effectiveDateTime`, exactly the FHIR path projected by
`ViewDefinition.lab_observation.json:14` and emitted as `charttime` by
`concept.sql:26`. The sole conflict was 1/117,898 rows (0.00085%), exactly
replayed as the America/New_York DST-gap normalization, consistent with its
rarity and unrecoverable from served FHIR. No other divergence classes were
present, and no dependencies diverged.

Judge outcome: the port is as faithful as the upstream data allows;
COMPLETED_WITH_DIVERGENCE is appropriate. Curated datetime/DST guidance in
`MIMIC_NOTES.md:337-403` was relevant. No new dataset-wide note was required.
