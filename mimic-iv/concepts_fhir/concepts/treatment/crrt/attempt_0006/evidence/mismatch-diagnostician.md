# Mismatch diagnostician evidence

The full-data divergence is upstream transformation loss, not a port bug. `mimic-fhir/sql/fhir_observation_chartevents.sql:9` casts source `charttime` through `TIMESTAMPTZ`, and line 67 writes the normalized timestamp to `Observation.effectiveDateTime`; the canonical CRRT query keeps source 02:xx and 03:xx groups separate before its `(stay_id, charttime)` pivot (`mimic-iv/concepts/treatment/crrt.sql:121-148`).

Attempt 0006 correctly parses the served FHIR time and preserves all observations before pivoting (`concept.sql:22-25,32-87`). The comparator's key attribution pairs 16 shifted keys, while the residual shifted rows collide with genuine 03:xx rows, producing 32 residual `only_oracle` rows and 26 conflicts. The original wall time is not recoverable by a permissible query: the pre-normalization timestamp used in `Observation.id` generation at `mimic-fhir/sql/fhir_observation_chartevents.sql:21` is opaque identity and cannot be inverted. The ETL emits one Observation per source row (`mimic-fhir/sql/fhir_observation_chartevents.sql:1,24-38`), so repeated-observation fan-out is not the cause.

Recommendation: route to the equivalence judge without retry or carryover invalidation. Divergence counts: 48 `only_oracle`, 16 `only_candidate`, 26 `differing_conflict`, 287,078 identical of 287,152 rows.
