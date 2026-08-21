# Mismatch diagnostician evidence

The diagnostician read the authoritative contract/notes, target and dependency
canonical SQL, target artifacts and comparison, completed `vitalsign` attempt
artifacts/comparison, manifest, and the upstream ETL SQL. The dependency list
from `ConversionController.divergent_dependencies` was `['vitalsign']`.

The 183 target conflicts are upstream transformation loss, not a target SQL
bug. Exhaustive decomposition found 176 inherited dependency effects from
`mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`, where charttime is cast
through `TIMESTAMPTZ` before `Observation.effectiveDateTime`; spring-forward
02:xx rows become 03:xx and can collide before the dependency and target
aggregations. Seven additional conflicts are direct ICU-anchor effects from
`mimic-fhir/sql/fhir_encounter_icu.sql:31,98`, where `icustays.intime` is
TIMESTAMPTZ-normalized into `Encounter.period.start`, changing membership in
the closed `[intime - 6h, intime + 1d]` window. There was no overlap, and no
only-oracle, only-candidate, or null-only residual.

The source wall times are absent from FHIR and cannot be recovered by any
query; resource identifiers remain opaque and were not used for inversion. The
target SQL correctly preserves the dependency boundary, opaque-key equality
join, inclusive window, and one-row-per-stay aggregation. The dependency's
hard-coded omitted event is outside this target's window. No carryover stage
requires invalidation, no new attempt is recommended, and the proven DST
second-order effects are not essential-loss blocks under the contract.
