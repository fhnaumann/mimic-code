# Divergence diagnosis — `acei`, attempt `0005`

The full-data `review` is `paired_residual` on the unkeyed concept: all 9,066
residual substitutions pair on `(acei, hadm_id, subject_id)`, with zero
unpaired rows. The 9,059 candidate-NULL values are intrinsic omitted validity
periods. The upstream ETL writes `MedicationRequest.dispenseRequest.validityPeriod`
only when the coalesced endpoints are present and ordered, at
`mimic-fhir/sql/fhir_medication_request.sql:172-177`; the oracle shows 9,050
reversed intervals, 8 start-only rows, and 1 stop-only row. `authoredOn` is
pharmacy `entertime`, not either source endpoint, and no other FHIR resource
retains the omitted times.

The 7 `differing_conflict` values are also intrinsic ETL transformation loss:
five `starttime` and three `stoptime` endpoints are normalized from source
02:xx to FHIR 03:xx by the `TIMESTAMPTZ` casts at
`mimic-fhir/sql/fhir_medication_request.sql:43-44`. This is non-injective and
cannot be inverted by a FHIR query; conditional subtraction would corrupt
genuine 03:xx values. The port's direct `TRY_CAST(... AS TIMESTAMP_NTZ)` is
correct. No carryover stage is invalidated, no new attempt is needed, and no
new dataset-wide note was appended because the curated notes already record
both quirks.

The result is ready for the equivalence judge at the required `contested` bar.
