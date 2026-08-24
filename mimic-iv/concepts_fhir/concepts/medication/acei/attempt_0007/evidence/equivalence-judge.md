## Evidence — equivalence-judge, acei attempt 0007

**Verdict: accept.** The full result is `review`, tier `gap_shaped`, with
`paired_residual` classification. All 112,014 rows are retained; 9,059
residual rows pair on `(acei, hadm_id, subject_id)` with no unpaired rows or
conflicts. Candidate NULLs affect `starttime` on 9,058 rows and `stoptime` on
9,051 rows.

The absent FHIR paths are
`MedicationRequest.dispenseRequest.validityPeriod.start` and `.end` for
invalid, reversed, or incomplete source intervals. The upstream ETL at
`mimic-fhir/sql/fhir_medication_request.sql:172-177` emits the validity period
only for complete, non-reversed intervals; no other FHIR path retains rejected
endpoints. `authoredOn` is pharmacy entry time and is not a substitute.

The direct and medication-mix ingredient branches, `UNION ALL` multiplicity,
exact validity paths, and `TRY_CAST(... AS TIMESTAMP_NTZ)` handling exhaust the
defensible mappings. The missing endpoints are ancillary: `acei.sql` performs
no temporal filtering, grouping, carry-forward, or clinical derivation, and
identity, admission, subject, row inclusion, and multiplicity remain exact.
No resource-id inversion is used. Fidelity is 102,955/112,014 identical
(91.9126%); no divergent dependencies exist. Current attempt 0007 has zero
conflicts, so no historical DST explanation is invoked.

The orchestrator should record this justification and transition to
`COMPLETED_WITH_DIVERGENCE`.
