# FHIR prober evidence

Read the contract, `MIMIC_NOTES.md`, and `carryover/arb/source-analyst.md`. Probed the authoritative demo Delta warehouse with embedded Pathling 9.6.0/Spark 4.0.2 and the read-only demo DuckDB oracle.

The mapping is pharmacy-backed `MedicationRequest` plus referenced `Medication`. Direct medication names use `medicationReference.getReferenceKey(Medication)` and a medication ViewDefinition projecting `identifier.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name').value`. Mix requests use `ingredient.itemReference.getReferenceKey(Medication)` and the same name identifier, with `UNION ALL` required to preserve multiplicity. Patient and hospital encounter identifiers are projected from `identifier.value` and joined through resource reference keys; SQL must cast the emitted strings to INTEGER. Validity fields are `dispenseRequest.validityPeriod.start/end`, offset-bearing strings requiring `TRY_CAST(... AS TIMESTAMP_NTZ)`.

Observed 17,552 MedicationRequests; 15,225 pharmacy-linked, 12,382 direct, 2,843 mix, 1,480 name Medications, and 634 resolving mix ingredient references. All 16 source tokens were checked. ARB rows totaled 35 in the demo oracle/direct candidate counts; 28 valid timestamps matched and seven reversed source intervals correctly appeared as FHIR NULL/NULL. Pharmacy `(pharmacy_id, drug)` multiplicity matched 18,087/18,087 across the complete probe. The full oracle manifest is unkeyed with `full_tuple_multiset`, target row count 39,534.

No new dataset-wide quirk was found; existing medication mix, identifier-string, omitted-invalid-period, and TIMESTAMP_NTZ notes apply.

Reusable artifact: `mimic-iv/concepts_fhir/carryover/arb/fhir-prober.md`, recorded with `mimic_utils carryover-record arb --stage fhir-prober`.
