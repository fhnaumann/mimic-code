# Evidence: mismatch-diagnostician (`first_day_bg`, attempt 0002)

The contested review is upstream transformation loss, not a port bug. The
current attempt reproduces the prior compared divergence; the new
`patient_key` and `icu_encounter_key` columns are excluded from value
comparison.

For specimen `44663261`, six labevents at source
`2151-03-14 02:02` are served as `03:02` because
`mimic-fhir/sql/fhir_observation_labevents.sql:15,121` casts and writes the
normalized `Observation.effectiveDateTime`. The alternative specimen time is
also normalized by `mimic-fhir/sql/fhir_specimen_lab.sql:9,18,58`, while
`Observation.issued` is storetime from `fhir_observation_labevents.sql:16,122`.
The original wall time is therefore absent from FHIR; resource ids are opaque
and cannot be inverted.

The shifted specimen-level dependency row is included by the relational
`first_day_bg` window at `02:02` but excluded at served `03:02` for stay
`33143532`, whose inclusive upper bound is `2151-03-14 02:30`. The resulting
single output-row divergence accounts for five conflicts
(`baseexcess_min`, `pco2_min`, `ph_max`, `po2_max`, `totalco2_min`) and four
candidate-null calculated fields (`aado2_calc_min/max`,
`pao2fio2ratio_min/max`). The dependency's four-hour FiO2 window explains the
calculated fields. No residual remains.

The full result is `73,180/73,181` identical, with `differing_conflict: 1`,
and no missing or invented rows. No carryover stage is at fault; no retry or
invalidation is recommended. The equivalence judge should decide the
contested review. No new dataset-wide quirk was found and the existing
`MIMIC_NOTES.d/first_day_bg.md` fragment was not modified.

Files checked included `comparison.full.json`, the current and prior attempt
SQL/ViewDefinitions/evidence, canonical SQL, `bg` attempt 0007, both
carryovers, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, and the cited upstream ETL
SQL files.
