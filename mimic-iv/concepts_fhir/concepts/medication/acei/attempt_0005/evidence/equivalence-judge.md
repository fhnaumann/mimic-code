# Equivalence judge evidence — `acei`, attempt `0005`

**Verdict: `accept`** at the `contested` bar.

The port is as faithful as the served FHIR data allows. The FHIR paths
`MedicationRequest.dispenseRequest.validityPeriod.start/end` are omitted for
invalid or incomplete source intervals by
`mimic-fhir/sql/fhir_medication_request.sql:172-177`, explaining all 9,059
null-only rows. `authoredOn` is pharmacy `entertime` (lines 55 and 124), not a
recoverable source endpoint. The seven conflicts are exact +1-hour DST-gap
rewrites from the `TIMESTAMPTZ` casts at
`mimic-fhir/sql/fhir_medication_request.sql:43-44`; the normalized values are
non-injective and no FHIR query can recover the original wall times.

All defensible mappings were exhausted: the medication-mix ingredient branch
and `UNION ALL` preserve multiplicity, and `TRY_CAST(... AS TIMESTAMP_NTZ)` is
the correct datetime handling. Schema and row counts match at 112,014;
102,948 rows are identical (91.91%), with 9,059 `differing_null_only` and 7
`differing_conflict` values. No divergent dependencies apply.

The judge also noted that the curated note's historical ACEI count of 14
predates the corrected parser; attempt 0005 establishes seven conflict rows
affecting eight endpoints. This is a note for orchestrator review only; the
judge wrote no files.
