# Evidence — equivalence-judge

Concept: `arb`; attempt: `0004`; verdict: `accept`; tier: `gap_shaped`.

The judge found that `MedicationRequest.dispenseRequest.validityPeriod.start`
and `.end` are absent for invalid or incomplete intervals. The ETL emits the
period only for complete, ordered endpoints at
`mimic-fhir/sql/fhir_medication_request.sql:172-177`; `authoredOn` is not an
endpoint substitute. This explains the 3,179 null-only residual rows
(`starttime`: 3,179; `stoptime`: 3,178). The port exhausted defensible mappings
using the medication-name identifier for direct and repeated medication-mix
ingredient paths, `UNION ALL` multiplicity, and `TRY_CAST(... AS TIMESTAMP_NTZ)`.

The two conflicting rows (one start and one stop) were exhaustively replayed
with zero residual to the upstream `TIMESTAMPTZ` cast at
`mimic-fhir/sql/fhir_medication_request.sql:43-44`; 2/39,534 (0.0051%) is
consistent with DST-gap rarity and the cited statement writes the sourced FHIR
element. No divergent dependencies exist. The loss is ancillary: `arb.sql`
does not use the endpoints for filtering, grouping, carry-forward, or another
derived clinical calculation, so the medication table remains faithful as far
as served FHIR permits.

Acceptance justification: the judge accepts the intrinsic gap and the
attributed upstream transformation, with no essential loss and no port bug.
No files were modified by the judge and no new dataset-wide quirk was found.
