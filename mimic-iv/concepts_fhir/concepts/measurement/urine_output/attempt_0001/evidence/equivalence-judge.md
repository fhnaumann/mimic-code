# Equivalence judge evidence

Concept: `urine_output`; attempt `0001`; comparator tier `attributed`; judge verdict: `bug`.

The machine replay was substantively plausible: 232 `differing_conflict`, 393 `only_oracle`, and 157 `only_candidate` findings were fully attributed to the America/New_York DST cast, with 236 key collisions and zero residual attribution rows. Identical fidelity was 3,321,123/3,321,748 (99.9812%); no columns were excluded. Canonical and candidate SQL both aggregate by `(stay_id, charttime)`, so collisions are an unavoidable consequence of normalized FHIR effective time, and no resource-id reconstruction was used.

The judge ruled `bug` because the comparator's `divergence.attributed[].citations` omitted the actual outputevents ETL writer. This concept sources `Observation.effectiveDateTime` and `valueQuantity.value`; the relevant provenance is `mimic-fhir/sql/fhir_observation_outputevents.sql:9,60,62-65`, where outputevent charttime is cast through `TIMESTAMPTZ`, written to `effectiveDateTime`, and value is written to `valueQuantity`. The listed chartevents/labevents/medication citations do not establish provenance for this outputevents stream. The attributed fraction itself is rare and plausible (393 shifted keys, 0.0118%), and both unpaired sets are fully accounted for, so after the citation defect is corrected the case is eligible for re-judgment rather than a candidate mapping change.

Divergent dependencies: none. No files were changed by the judge and no commit was made.

Required remediation: add the outputevents ETL citation to the comparator's known DST citation set, create a fresh immutable attempt, and rerun full data. Do not reconstruct or parse resource IDs.
