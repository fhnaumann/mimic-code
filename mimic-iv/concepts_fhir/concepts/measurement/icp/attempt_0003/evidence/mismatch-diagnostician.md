Evidence block

The diagnostician read the full comparison and attempt artifacts, canonical
source SQL, authoritative MIMIC notes, and upstream ETL. It classified the
divergence as upstream ETL transformation loss, not a port bug. The ETL casts
chartevents `charttime` through `TIMESTAMPTZ` at
`/Users/nau025/Documents/mimic-fhir/sql/fhir_observation_chartevents.sql:9`
and writes the normalized value as `Observation.effectiveDateTime` at line 67.
Nonexistent New York spring-forward 02:xx times become 03:xx irreversibly.

All 17 oracle-only rows have the DST signature. Two re-pair as candidate-only
03:10/03:20 rows; 15 collide at 03:00, with four grouped `icp` maxima changing
and producing `differing_conflict`. The pre-cast value affects only UUID
generation at ETL line 21; resource IDs are opaque and cannot be inverted.
The source `value IS NOT NULL` and hard-coded duplicate predicates were checked
and do not explain these rows. No carryover stage was invalidated and no
artifacts were modified.

Recommendation: retain the current non-inverting `TIMESTAMP_NTZ` mapping and
send the cited upstream loss to the equivalence judge. No fragment was appended.
