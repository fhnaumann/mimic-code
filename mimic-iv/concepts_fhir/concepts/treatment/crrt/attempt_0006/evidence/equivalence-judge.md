# Equivalence judge evidence

Verdict: `accept` for attempt `0006`, tier `contested`.

The port reproduces 287,078/287,152 oracle rows identically (99.9742%); divergence is 48 `only_oracle`, 16 `only_candidate`, 26 `differing_conflict`, and 0 `differing_null_only`. The comparator pairs all 16 candidate-only keys with oracle-only keys through the New York DST shift; the remaining 32 source 02:xx rows collide with genuine 03:xx pivot keys, changing 26 destination pivots.

The port sources `Observation.effective.ofType(dateTime)` (`ViewDefinition.crrt_observation.json:11`, `concept.sql:22-25`). Upstream `mimic-fhir/sql/fhir_observation_chartevents.sql:9` casts `charttime` through `TIMESTAMPTZ`, and line 67 writes the normalized value. The original wall time is unrecoverable by permissible FHIR queries; its presence only in opaque UUIDv5 identity at line 21 cannot be used for recovery. The canonical source pivots original `(stay_id, charttime)` at `mimic-iv/concepts/treatment/crrt.sql:121-148`, while the candidate correctly pivots served effective time.

All defensible mappings were exhausted, no dependencies inherit divergence, and the affected rows represent the contract's accepted irreversible New York DST normalization rather than essential clinical source loss. No new dataset-wide quirk was found and no notes fragment was appended.
