# Evidence: equivalence-judge (`first_day_bg`, attempt 0002)

**Verdict: `accept`** for the `review`, tier `contested` result.

The judge accepted the wholly inherited upstream DST divergence. The cited
source is `mimic-fhir/sql/fhir_observation_labevents.sql:15,121`, which casts
`labevents.charttime` through `TIMESTAMPTZ` and writes the normalized value to
`Observation.effectiveDateTime`; `bg` exposes that value as `bg.charttime`.
`mimic-fhir/sql/fhir_specimen_lab.sql:9,18,58` repeats the normalized time,
and `Observation.issued` is storetime at `fhir_observation_labevents.sql:16,122`.
The original wall time is therefore unrecoverable by any FHIR query without
forbidden resource-ID inference.

Six labevents for specimen `44663261` moved from `2151-03-14 02:02` to
`03:02`. For stay `33143532`, the served dependency row crosses the inclusive
`first_day_bg` upper bound and changes one row's aggregates. All nine field
incidences are explained: five conflicts and four calculated candidate-null
fields. There is no residual. The contract's upstream DST-defect exemption
applies even though the shift changes time-window inclusion and clinical
aggregates.

Fidelity: 73,180/73,181 rows identical (99.998633%); one
`differing_conflict`; no `only_oracle`, `only_candidate`, or
`differing_null_only`. Divergent dependency: `bg`, already
`COMPLETED_WITH_DIVERGENCE`. No new dataset-wide quirk was found and no
fragment was modified.

Files read: `LOOP_CONTRACT.md`, curated `MIMIC_NOTES.md`, current and prior
comparisons/SQL/ViewDefinitions, canonical SQL, accepted `bg` state and
artifacts, and the cited upstream ETL SQL. No files were modified by the
judge.
