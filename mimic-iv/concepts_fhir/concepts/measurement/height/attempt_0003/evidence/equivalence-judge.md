# Evidence — equivalence-judge

The judge returned `accept` for the full-data `review`, tier `attributed`.
`mimic-fhir/sql/fhir_observation_chartevents.sql:9` casts source charttime
through `TIMESTAMPTZ` and line 67 writes the transformed value to
`Observation.effectiveDateTime`; the port reads that element directly and
casts to `TIMESTAMP_NTZ`. The comparator replayed this transformation on all 2
conflicting rows with zero residual. The affected fraction is 2/33,474
(0.006%), consistent with DST-gap rarity. Height values, row inclusion,
ancillary and intrinsic rather than essential.

Judge citation: `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`.
Verdict: `accept`.
