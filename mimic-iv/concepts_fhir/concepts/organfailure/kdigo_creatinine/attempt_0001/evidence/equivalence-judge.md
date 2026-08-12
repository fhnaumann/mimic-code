# Equivalence-judge evidence

Verdict: `accept` for the `contested` review. The judge independently confirmed that `mimic-fhir/sql/fhir_observation_labevents.sql:15,121` irreversibly transforms source `labevents.charttime` through `TIMESTAMPTZ` before writing `Observation.effectiveDateTime`; the parallel specimen path repeats this at `mimic-fhir/sql/fhir_specimen_lab.sql:18,58`. Only `labevent_id` provenance remains, so normalized DST-gap 03:xx cannot be distinguished from genuine 03:xx and exact source chronology/window membership is unrecoverable.

The accepted divergence is 160 `differing_conflict` rows out of 599,607 (99.9733% identical): charttime 145, creat 1, prior-48-hour minimum 17, prior-seven-day minimum 9. The comparator directly attributed 138 rows; the diagnostician explained 21 of the remaining 22 as downstream window effects and the final one as within-tolerance floating representation. No missing, invented, or null-only rows occurred. No retry is warranted.
