# Equivalence judge evidence

Verdict: `accept` for attempt 0002, with `review` tier `contested` and classification `unavailable_no_key`.

The judge accepted an intrinsic upstream transformation loss. For 3,182 of 39,534 rows (8.049%), the ETL reads source endpoints at `/Users/nau025/Documents/mimic-fhir/sql/fhir_medication_request.sql:43-44` but writes `MedicationRequest.dispenseRequest.validityPeriod.start/end` only for complete non-reversed intervals at `:172-177`; affected invalid/incomplete endpoints therefore become NULL and are unrecoverable. `authoredOn` is unrelated pharmacy entry time (`:55,124`), and medication/mix ETL preserves names and ingredients but no prescription endpoints (`medication_prescriptions.sql:19-58`; `medication_mix.sql:27-53,64-85`).

The unkeyed comparison reports paired 3,182 candidate-only NULL-period and 3,182 oracle-only timestamp tuples; row counts and schema match. The candidate correctly covers direct and mix branches, multiplicity, all 16 filters, identifier joins, and TIMESTAMP_NTZ parsing. `divergent_dependencies('arb')` returned `[]`. No retry is warranted, no new shared note was found, and no files were modified by the judge.

Acceptance justification: the missing FHIR `MedicationRequest.dispenseRequest.validityPeriod.start/end` path and cited ETL condition explain the divergence, while no alternate FHIR element preserves the original timestamps. The port is faithful as transformed data permits.
