Evidence block

Concept: `oxygen_delivery`; attempt `0003`; verdict: `accept`; tier: `attributed`.

The judge confirmed that `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` casts source `charttime` through `TIMESTAMPTZ` and writes it to `Observation.effectiveDateTime`, which the attempt maps through `(effective).ofType(dateTime)` and `TIMESTAMP_NTZ`. The affected event fraction is 34 unique events out of 601,546 (approximately 0.0057%), consistent with one DST spring-forward hour per year. Comparator attribution is exhaustive with zero residuals: 31 re-keyed events and three occupied-key collisions.

The judge independently confirmed from the canonical and candidate SQL that the three collisions propagate through flow-code merging, `issued`/storetime ranking, device ranking, flow-to-device joining by patient and charttime, and grouping/pivoting by patient and charttime. The original 02:xx wall time is overwritten before FHIR serialization and is not recoverable by a compliant query. Resource keys were not parsed or regenerated. The proven upstream DST normalization is accepted under the contract and is not essential-loss blocking.

Overall fidelity: 601,509/601,546 identical (99.9938%); no columns excluded or declared unrepresentable. Divergent dependencies: none. Relevant curated notes were the datetime `TIMESTAMP_NTZ`, chartevents downstream DST, categorical `valueString`, opaque resource key, and verbatim itemid entries. No new dataset-wide quirk was discovered or appended.

Acceptance justification: intrinsic upstream DST normalization at `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` accounts for all 34 affected events and the three aggregation collisions with zero residual; the port is faithful to the served FHIR data and no compliant query can recover the original wall time.
