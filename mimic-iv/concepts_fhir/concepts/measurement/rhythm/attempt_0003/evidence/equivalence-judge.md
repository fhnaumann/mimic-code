# Equivalence-judge evidence

- Concept/attempt: `rhythm`, `0003`; verdict: `accept`; tier: `attributed`.
- Divergence: 95 `differing_conflict`, 645 `only_oracle`, and 42 `only_candidate`; all candidate-only keys re-paired after DST replay, 603 oracle-only rows collided with existing candidate keys, and residuals were zero. The 95 collision rows altered aggregates.
- Fidelity: 5,872,983/5,873,723 identical rows (99.9874%); no columns were excluded as unrepresentable. The 645 shifted events are 0.0110% of oracle rows, consistent with one DST-gap hour per year.
- Provenance: `mimic-fhir/sql/fhir_observation_chartevents.sql:9` casts `ce.charttime` through `TIMESTAMPTZ` and line 67 writes it to `Observation.effectiveDateTime`; the candidate sources charttime from `effective.ofType(dateTime)`. The original wall time is not recoverable from FHIR, and resource IDs were not used as a semantic channel.
- Aggregation check passed: both canonical and candidate SQL group by `(subject_id, charttime)`; ordered distinct `collect_set`/sorting plus `concat_ws('; ', ...)` matches ordered-distinct `STRING_AGG`, and ectopy fields use lexical `MAX`. This explains the collision values.
- Dependencies: none divergent. The current port applies the curated datetime, categorical valueString, exact item-code, and opaque-key rules. The judge accepted the exhaustively proven upstream transformation under the contract's DST exemption.
