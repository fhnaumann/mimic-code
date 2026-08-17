# Equivalence-judge evidence

The independent judge read `LOOP_CONTRACT.md`, curated
`MIMIC_NOTES.md`, the current and prior implementation/comparison artifacts,
the reused attempt-0002 diagnosis, and controller state. Divergent
dependencies were `[]`. It returned **accept** for the contested review.

The judge confirmed that `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`
writes normalized chartevent times to `Observation.effectiveDateTime`, and
`mimic-fhir/sql/fhir_encounter_icu.sql:31-32,97-100` writes normalized ICU
times to `Encounter.period.start/end`. The canonical and candidate
`ROW_NUMBER`/`LEAD`, two-hour ICU arithmetic, backfill, and `UNION ALL`
constructs propagate one shifted source event into the observed interval/key
effects. Full replay closes all 38 oracle-only and 32 candidate-only rows,
including six collisions, and closes the 17 residual conflicts as nine ICU
arithmetic and eight chartevents/LEAD effects. The affected 56/272,445
conflicts (0.0206%) are DST-rare; original wall times are unrecoverable from
FHIR, and no resource-id inversion was used. The required resource-key columns
are opaque, additive identity columns excluded from the compared projection.

The accepted justification is that attempt 0003 reproduces every value
obtainable from served FHIR and diverges only through the cited upstream
America/New_York DST normalization and its second-order effects through the
concept SQL. The judge applied the contract's explicit DST exception despite
timing/key and one weight assignment being affected; this is not essential-loss
blocking.
