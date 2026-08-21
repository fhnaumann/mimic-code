# Mismatch-diagnostician evidence — `urine_output_rate`, attempt 0002

The diagnostician read the current comparison, SQL/ViewDefinitions, canonical
SQL, curated `MIMIC_NOTES.md`, and completed dependency artifacts. The
remaining 1,185 conflicts are not a new candidate bug. They are second-order
propagation of upstream DST-normalized timestamps through the completed
`urine_output` and `weight_durations` dependencies and this concept's own
rolling windows and interval overlay.

The completed `urine_output` attempt has the same 393/157 key fingerprint and
232 collision conflicts, exhaustively attributed to
`mimic-fhir/sql/fhir_observation_outputevents.sql:9,60,62-65`. The shifted
dependency `charttime` propagates through `LAG`/elapsed time at
`concept.sql:48-64`, window sums at `:74-143`, and rates at `:173-211`, so
later non-03:00 rows can differ. Completed `weight_durations` has accepted
ICU-period arithmetic effects from
`mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` and
`mimic-fhir/sql/fhir_encounter_icu.sql:31-32,97-100`; its shifted interval
boundaries propagate through the strict/inclusive weight join at
`concept.sql:159-163`, explaining the 10 weight conflicts and associated
rate effects. The heart-rate anchor also uses normalized chartevents times.

The original wall times are overwritten before FHIR serialization and cannot
be recovered by any FHIR query. Resource ids remain opaque and cannot be used
for repair. Source/FHIR carryover is correct; no carryover invalidation or new
attempt is warranted. This is judge-ready as an upstream transformation-loss
diagnosis, with the current port preserving dependency boundaries and
canonical semantics.
