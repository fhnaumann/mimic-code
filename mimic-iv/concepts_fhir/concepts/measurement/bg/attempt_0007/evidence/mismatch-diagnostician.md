# Mismatch diagnosis — `bg`, attempt 0007

The diagnostician read the immutable comparison artifact, attempt SQL and
ViewDefinitions, canonical `bg.sql`, both `bg` carryover analyses, curated
`MIMIC_NOTES.md`, and the upstream labevents, chartevents, and lab-specimen ETL
SQL. The relevant sibling fragment lead in `MIMIC_NOTES.d/first_day_bg.md` was
treated as provisional and independently verified.

The six residual conflicts are not a port bug. They are second-order effects of
the upstream labevents DST transformation. Six specimens have 57 selected
labevents rows, all at source 02:xx times, and all 57 are normalized to 03:xx
by `mimic-fhir/sql/fhir_observation_labevents.sql:15,121`. For each residual,
an unshifted 03:00 FiO2 chart event falls outside the canonical four-hour
latest-preceding window but inside the candidate window after the blood-gas
anchor is shifted. The candidate therefore selects a different FiO2, changing
`fio2_chartevents` and, where lab FiO2 does not take precedence,
`aado2_calc`/`pao2fio2ratio`. The current SQL's `MAX(charttime)`, window join,
and calculations match the canonical semantics; `TIMESTAMP_NTZ` is correct.

The 64 directly attributed conflicts plus these six residuals close the full
70-conflict set. `Observation.issued` is storetime and does not preserve the
source charttime; `Specimen.collection.collectedDateTime` repeats the same loss
(`mimic-fhir/sql/fhir_specimen_lab.sql:9,18,58`). The original 02:xx wall time
is unrecoverable from served FHIR, and resource IDs are opaque and were not
used. The ETL citation and propagation account are sufficient for the judge;
no semantic fix, retry, or carryover invalidation is recommended.

No new `MIMIC_NOTES.d/bg.md` entry was appended by the diagnostician. The
sibling lead is eligible for orchestrator self-promotion to curated notes only
after this concept receives a successful terminal verdict.
