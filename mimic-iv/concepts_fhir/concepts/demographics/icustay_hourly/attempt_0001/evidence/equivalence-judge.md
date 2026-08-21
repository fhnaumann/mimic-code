# Equivalence judge evidence — icustay_hourly

Verdict: **accept** for comparator `review`, tier `contested`.

The divergence is wholly inherited from the sole divergent dependency
`icustay_times`. Upstream
`mimic-fhir/sql/fhir_observation_chartevents.sql:9` casts `chartevents.charttime`
through `TIMESTAMPTZ`, and line 67 writes the normalized value to
`Observation.effectiveDateTime`. Canonical `mimic-iv/concepts/demographics/icustay_times.sql:4-11`
aggregates MIN/MAX before this transformation. A full-oracle replay found 696
selected HR rows shifted across 643 stays, yielding exactly seven changed
minima and one changed maximum.

Passing those endpoints through the correct target expansion at
`mimic-iv/concepts/demographics/icustay_hourly.sql:15-35` reproduced every
target divergence with zero residual: 7 `only_oracle`, 1 `only_candidate`, and
60 `differing_conflict` rows, all conflicts on `hr`. Six minima removed one
terminal oracle row each; stay 36521920 produced one missing row and 60 shared
keys with candidate `hr` one lower; stay 32933486 produced the sole
candidate-only row. The candidate has no target-local bug.

The original wall time is unrecoverable by any allowed query. FHIR carries only
the normalized effective timestamp; `issued` is transformed storetime, not
charttime. The UUID's pre-cast charttime input is opaque identity and cannot be
parsed or inverted, and ICU Encounter periods cannot substitute for HR
observation times. The affected endpoint fraction was 8/73,181 (0.0109%); all
68 target divergence rows are accounted for. Although the shift changes row
inclusion, keys, and generated timing, the loop contract explicitly accepts a
proven New York DST transformation and its second-order effects rather than
blocking it as essential loss.

Acceptance justification: all 68 classified target divergences are exhaustively
explained as second-order propagation of the accepted `icustay_times` DST
defect at `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`; the source
wall time is absent from all semantic FHIR fields, every defensible legal
mapping was applied, and zero target-local residual remains.

No new dataset-wide quirk was found; the existing target fragment entry already
records the chartevents MIN/MAX normalization claim.
