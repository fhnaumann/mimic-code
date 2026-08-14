# Equivalence judge evidence

Concept: `urine_output`; attempt `0002`; judge verdict: `accept` for the `attributed` review.

Justification: Upstream `mimic-fhir/sql/fhir_observation_outputevents.sql:9` casts `outputevents.charttime` through `TIMESTAMPTZ`, writes it to `Observation.effectiveDateTime` at line 60, and writes source values to `Observation.valueQuantity.value` at lines 62–65. The candidate reads those exact paths and applies the canonical item filters, `227488` negation, and `SUM ... GROUP BY (stay_id, charttime)`. DST-shifted 02:xx rows landing on occupied 03:xx keys therefore aggregate together; 236 collisions account for all 232 urine-output conflicts. Comparator replay accounts for all 393 `only_oracle` and 157 `only_candidate` rows with zero residual. The 393 shifted keys are 0.0118% of oracle rows, consistent with DST-gap rarity. No resource-ID reconstruction is used and the original wall time is unrecoverable.

Fidelity: identical and representable fractions are both 99.9812% (3,321,123/3,321,748), with no excluded or declared-unrepresentable columns. Divergence: 393 `only_oracle`, 157 `only_candidate`, 232 `differing_conflict`, and 236 key collisions, all attributed with zero residual. Divergent dependencies: none.

Required orchestrator action: record this accepted intrinsic upstream transformation with `mimic_utils accept-divergence urine_output --justification` using the cited reason. The judge made no state transition or file edits.
