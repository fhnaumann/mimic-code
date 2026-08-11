# FHIR-prober evidence — gcs attempt_0001

The authoritative demo Delta was probed with embedded Pathling 9.6.0 on Spark
4.0.2, alongside the read-only DuckDB demo oracle. The three source itemids
map to `Observation.code.coding` under
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`, with
9,791/9,791 exact source/FHIR tuples and one coding per resource. Subject and
ICU stay identifiers require reference-key joins followed by casts of
`identifier.value` strings to INTEGER. `effective.ofType(dateTime)` is the
only populated effective choice and must be parsed as `TIMESTAMP_NTZ`.
Quantity values are materialized string-like and must be cast to FLOAT; the
source text sentinel is not exposed as `valueString`.

The prober found the exact `No Response-ETT` text on 1,348 source rows, but
FHIR stores all verbal rows as Quantity 1, conflating those with 78 ordinary
`No Response` rows. No quantity-1 heuristic is exact; the ETL UUID input can
serve only as a finite candidate witness, not a standard FHIRPath mapping.
Selected demo rows had no NULL `value`, while the ETL-wide `value IS NOT NULL`
filter remains a potential full-data coverage gap. The owned notes fragment was
append-updated with the dataset-wide numeric-chartevents text-loss finding.

Reusable mapping was written and recorded at
`mimic-iv/concepts_fhir/carryover/gcs/fhir-prober.md`. No ViewDefinition or SQL
was created by this stage.
