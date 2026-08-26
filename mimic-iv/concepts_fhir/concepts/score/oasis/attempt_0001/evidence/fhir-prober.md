# FHIR-prober evidence

Concept: `oasis`; attempt: `0001`.

The prober read the source-analysis carryover, the curated notes and relevant
provisional fragments, the canonical OASIS/dependency interfaces, and the
oracle manifest. It used embedded Pathling 9.6.0 on Spark 4.0.2 over the
authoritative local Delta warehouse, with the DuckDB demo oracle for
cross-checks; it did not use HTTP Pathling or stale NDJSON.

It verified the opaque identifier/reference spine: Patient identifiers,
hospital and ICU Encounter streams selected by exact identifier systems,
Encounter `period` endpoints, `partOf`/`subject` equality joins, and required
type-prefixed resource-key columns. It verified the exact chartevent and
outputevent code systems and dependency code sets, dateTime-only effective
variants, Quantity projections, and rebuilt chartevent component text. The
five completed dependency stems are to be consumed at their published key and
value interfaces, not re-derived from FHIR.

The prober found that `Encounter.serviceType` provides one current service
coding per hospital Encounter while source `services` has history and
`transfertime`; the OASIS surgical predicate was not exactly recoverable. It
also confirmed that absent mortality intermediates are not selected by the
final OASIS output. The service-history finding is dataset-wide and was
appended to the owned fragment:
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/oasis.md`.

Reusable mapping artifact written and recorded:
`mimic-iv/concepts_fhir/carryover/oasis/fhir-prober.md` and
`mimic-iv/concepts_fhir/carryover/oasis/carryover.json`.
No ViewDefinition, `concept.sql`, execution, or commit was performed by this
stage.
