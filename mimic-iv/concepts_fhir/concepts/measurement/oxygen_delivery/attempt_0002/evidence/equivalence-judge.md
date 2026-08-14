# Evidence: equivalence-judge

Verdict: `accept` for the full-data `review`, tier `attributed`.

The comparator fully attributed 34 `only_oracle`, 31 `only_candidate`, and 3 `differing_conflict` findings to irreversible DST normalization of the chartevents charttime. The three conflicts are occupied-key collisions corresponding to three oracle-only events, not additional independent events; key and conflict attribution both have zero residual. The affected fraction is 34/601,546 (about 0.0057%), consistent with one spring-forward hour per year.

The actual provenance is `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`, which transforms `ce.charttime` through `TIMESTAMPTZ` before writing `Observation.effectiveDateTime`. The port projects `(effective).ofType(dateTime)` and casts it to `TIMESTAMP_NTZ`, preserving the served wall time. The collision values accord with oxygen_delivery's own flow/device ROW_NUMBER ranking, patient/charttime join, and final GROUP BY/MAX semantics. The original 02:xx wall time is unrecoverable from semantic FHIR elements; resource IDs remain opaque and were not inverted.

Full fidelity: 601,509/601,546 identical (99.9938%); no declared or excluded columns. The contract expressly permits acceptance of a completely machine-attributed intrinsic New York DST normalization, including this aggregation-sensitive collision case. No new dataset-wide quirk was identified and no diagnostician was required.

Judge justification:

> Accepted intrinsic DST normalization: `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` transforms source charttime through `TIMESTAMPTZ` before writing `Observation.effectiveDateTime`. Full replay accounts for all 34 affected events—31 re-keyed rows and three occupied-key collisions causing the three aggregate conflicts—with zero residual. The collision values follow oxygen_delivery's own ROW_NUMBER, GROUP BY, and MAX semantics. The pre-shift wall time is unrecoverable without prohibited resource-id inversion.
