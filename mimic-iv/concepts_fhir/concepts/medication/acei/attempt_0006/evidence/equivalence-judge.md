# Equivalence judge evidence — acei attempt 0006

- The independent judge read the loop contract, curated `MIMIC_NOTES.md`, the
  current comparison and run metadata, current SQL/ViewDefinitions, the
  canonical source SQL, upstream MedicationRequest ETL, and prior attempt
  comparison history. No fragment was cited and no file was modified.
- Verdict: `accept` for the `gap_shaped` review.
- The absent FHIR paths are
  `MedicationRequest.dispenseRequest.validityPeriod.start` and `.end` for
  reversed or incomplete source intervals. Upstream
  `mimic-fhir/sql/fhir_medication_request.sql:172-177` omits the period in
  those cases; `authoredOn` is pharmacy entertime and is not a substitute.
  This explains all 9,059 paired null-only endpoint differences (9,050
  reversed plus 9 incomplete ACEI intervals) without invented or unpaired
  rows.
- The judge confirmed the direct and medication-mix `UNION ALL` mapping,
  exact validity paths, `TIMESTAMP_NTZ`, opaque equality joins, required
  support keys, and no resource-id inversion. The missing endpoints are
  ancillary for this concept: no row inclusion, grouping, semantic grain,
  carry-forward, or derived clinical calculation depends on them.
- The seven conflicts (5 starttime, 3 stoptime; 7/112,014 = 0.00625%) are
  exhaustively attributed with zero residual to the upstream
  `TIMESTAMPTZ` casts at `mimic-fhir/sql/fhir_medication_request.sql:43-44`
  feeding the validity elements at `:172-177`; the fraction is consistent
  with DST-gap rarity.

Judge citation for acceptance:

`MIMIC-on-FHIR omits MedicationRequest.dispenseRequest.validityPeriod.start/end for 9,050 reversed and 9 incomplete ACEI intervals, producing exactly 9,059 paired null-only rows, while seven additional endpoint conflicts are exhaustively attributable to the upstream TIMESTAMPTZ casts at mimic-fhir/sql/fhir_medication_request.sql:43-44 feeding the elements written at :172-177. The complete direct-plus-mix mapping preserves every row and uses no resource-id inversion; the missing endpoints affect no inclusion, grouping, grain, carry-forward, or derived output.`
