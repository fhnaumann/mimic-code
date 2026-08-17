# Equivalence-judge evidence — `bg`, attempt 0007

The independent judge read the authoritative contract, curated
`MIMIC_NOTES.md`, the current attempt's five ViewDefinitions and SQL, canonical
`measurement/bg.sql`, the full comparison, and the diagnostician evidence. It
returned **accept** for the `contested` review.

The judge accepted the 70 paired `differing_conflict` incidences: 64 are
machine-replayed DST-gap conflicts and six are fully accounted for as
second-order effects of 57 labevents rows shifted through bg's four-hour FiO2
window. The upstream citation is
`mimic-fhir/sql/fhir_observation_labevents.sql:15,121`; corroborating specimen
loss is `mimic-fhir/sql/fhir_specimen_lab.sql:9,18,58`. The original 02:xx wall
time is absent from served FHIR, `Observation.issued` is storetime, and resource
IDs are opaque and were not used. The affected fraction, 70/511,637 (0.0137%),
fits DST-gap rarity. No essential-loss block applies under the contract's
upstream DST-defect rule, and no retry is needed.

Accepted justification:

> Accepted intrinsic upstream divergence: `mimic-fhir/sql/fhir_observation_labevents.sql:15,121` irreversibly normalizes DST-gap `charttime` before writing `Observation.effectiveDateTime`. Comparator replay explains 64 conflicts, and six further conflicts are fully accounted for as second-order effects through bg’s four-hour FiO2 window. `Observation.issued` is storetime and `Specimen.collection.collectedDateTime` repeats the same normalized timestamp (`fhir_specimen_lab.sql:9,18,58`), so the oracle wall time is unrecoverable from served FHIR without forbidden resource-ID inference.
