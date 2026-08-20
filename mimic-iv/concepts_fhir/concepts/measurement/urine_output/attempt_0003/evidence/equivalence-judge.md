# Evidence: equivalence-judge

The independent judge reviewed the attributed full-data `review` without a diagnostician. Verdict: **accept**.

The judge confirmed `mimic-fhir/sql/fhir_observation_outputevents.sql:9` casts `outputevents.charttime` through `TIMESTAMPTZ`, line 60 writes the normalized value to `Observation.effectiveDateTime`, and lines 62-65 preserve the source value in `Observation.valueQuantity.value`. Attempt 0003 reads those paths, applies `TIMESTAMP_NTZ`, the exact twelve itemids, the positive `227488` sign rule, and the canonical `(stay_id, charttime)` sum. The comparator exhaustively accounted for 393 `only_oracle`, 157 `only_candidate`, and 232 `differing_conflict` rows with zero residual; 157 keys re-paired and 236 collided into occupied keys, producing the aggregate conflicts. The 393 shifted keys are 0.0118% of oracle rows, consistent with DST-gap rarity. No FHIR element preserves the original 02:xx wall time, and resource IDs remain opaque and were not inverted. Under the contract, proven DST divergence, including aggregation effects, is accepted rather than blocked.

Fidelity: 3,321,123/3,321,748 identical (99.9812%); no columns excluded. Divergence classes: `only_oracle` 393, `only_candidate` 157, `differing_conflict` 232, `differing_null_only` 0. No divergent dependencies. No new dataset-wide quirk was found or appended.
