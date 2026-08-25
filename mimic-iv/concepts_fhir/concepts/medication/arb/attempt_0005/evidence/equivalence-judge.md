# Equivalence judge evidence — arb attempt 0005

The independent judge read the loop contract, curated MIMIC notes, canonical
`arb.sql`, the carried port artifacts, the full comparison and run metadata,
replay provenance, state history, prior evidence, and the upstream medication
request ETL. It returned `accept` for the `gap_shaped` review.

The judge cited `mimic-fhir/sql/fhir_medication_request.sql:43-44` for reading
the source endpoints and `:172-177` for emitting `validityPeriod` only when
both endpoints are present and non-reversed. This explains 3,179 null-only
substitutions: 3,178 rows lose both endpoints and one loses only its non-NULL
start. `authoredOn` at `:55,124` is pharmacy `entertime`, not either endpoint.
The candidate tried direct and medication-mix ingredient paths, preserved
multiplicity, selected the validity paths directly, and used the required
`TRY_CAST(... AS TIMESTAMP_NTZ)`. The canonical `arb.sql:19-30` uses endpoints
only as projected outputs, so their absence does not alter inclusion, grain,
grouping, carry-forward, or a derived clinical output. All 39,534 rows remain
represented.

Judge result: `accept`; no artifacts were written by the judge.
