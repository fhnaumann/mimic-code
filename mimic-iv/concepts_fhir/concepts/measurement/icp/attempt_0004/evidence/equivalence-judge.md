# equivalence-judge evidence

Concept: `icp`; attempt: `0004`; comparator tier: `attributed`; judge verdict:
`accept`.

The judge confirmed provenance from the candidate's
`Observation.effective.ofType(dateTime)` path and
`mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`, where source
`chartevents.charttime` is cast through `TIMESTAMPTZ` and written to
`Observation.effectiveDateTime`. The attributed fraction is rare and
consistent with DST-gap events: 17 shifted source events among 173,273 oracle
rows, with 4 collisions changing the grouped `MAX` result. The 2 repaired
key moves and 15 occupied-key collisions close all `only_oracle`,
`only_candidate`, and conflict residuals; the four value conflicts are the
canonical and candidate range-gated `MAX` behavior over the collided groups.

The judge verified that the candidate is faithful to the served FHIR
representation, no admissible path recovers the overwritten wall time, and
the attempt does not reconstruct or parse `Observation.id`. No divergent
dependencies were present and no essential source loss was alleged. Verdict:
judge-accepted divergence, suitable for `COMPLETED_WITH_DIVERGENCE`.

Fidelity: 173,252/173,273 identical (99.9879%); representable fidelity is the
same because no columns were excluded as unrepresentable. No new dataset-wide
quirk was identified.
