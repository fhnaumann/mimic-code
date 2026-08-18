# Equivalence judge evidence — enzyme attempt 0003

Verdict: `accept` for the attributed review.

- The judge confirmed 65 `differing_conflict` rows, all on `charttime`, with 1,639,449/1,639,514 identical rows, zero missing/candidate-only/null-only rows, matching schemas, and matching row counts.
- The comparator exhaustively replayed every conflict as `upstream_timestamptz_dst_shift` in `America/New_York`, with zero residual; 65/1,639,514 (0.00396%) is consistent with a one-hour-per-year DST-gap event.
- `mimic-fhir/sql/fhir_observation_labevents.sql:15,121` writes the transformed value read from `Observation.effectiveDateTime`; `mimic-fhir/sql/fhir_specimen_lab.sql:18,58` likewise preserves only the normalized specimen collection time. The original 02:xx wall time is absent from FHIR and cannot be recovered by a query.
- The port uses `TIMESTAMP_NTZ`, no resource-id semantic side channel, and no divergent dependencies exist. The judge found no essential representation loss and accepted the intrinsic upstream transformation.
