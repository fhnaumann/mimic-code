# Evidence: equivalence-judge

Verdict: `accept` for the attributed review.

The judge confirmed that the port reads `Observation.effectiveDateTime` through `(effective).ofType(dateTime)` (`ViewDefinition.lab_observation.json:14`) and preserves the served wall value with `TRY_CAST(... AS TIMESTAMP_NTZ)` (`concept.sql:31`). The upstream ETL casts labevents `charttime` through `TIMESTAMPTZ` at `mimic-fhir/sql/fhir_observation_labevents.sql:15` and serializes that transformed value as `Observation.effectiveDateTime` at `:121`; the parallel lab Specimen path is likewise cited at `mimic-fhir/sql/fhir_specimen_lab.sql:18,58`. The comparator exhaustively replayed the sole conflict as this America/New_York spring-forward normalization with zero residual. The affected fraction is 1/117,898 = 0.000848%, consistent with DST-gap rarity, and the original 02:07 wall time is unrecoverable from FHIR. Under the contract's DST exemption this is accepted, not essential source loss.
