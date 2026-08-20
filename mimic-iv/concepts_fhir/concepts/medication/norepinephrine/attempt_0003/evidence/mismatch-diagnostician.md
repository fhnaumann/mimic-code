# Mismatch diagnosis — norepinephrine attempt_0003

The attempt_0002 two-row `vaso_rate` bug is fixed. Full-oracle probing found
exactly two `mg/kg/min` rows, both with `patientweight=1`, and all remaining
335,998 rows use the raw-rate branch; attempt_0003's unconditional raw FHIR
rate cast at `concept.sql:37` is therefore correct. No current port bug or
carryover fault was found, so no retry or carryover invalidation is required.

The full diff is a VOID-DIFF artifact: `linkorderid` is honestly emitted as
typed NULL and declared unrepresentable, but the manifest key is
`(linkorderid,starttime)`. The equal 336,000 row counts and symmetric
336,000-only residuals do not indicate invention or omission. The canonical
query has no join, grouping, DISTINCT, or aggregation
(`mimic-iv/concepts/medication/norepinephrine.sql:3-16`), and the ETL emits one
MedicationAdministration per inputevent
(`mimic-fhir/sql/fhir_medication_administration_icu.sql:1,20,24-40`), so the
candidate preserves row multiplicity. `linkorderid` is projected only by the
source SQL and does not affect inclusion, derivation, grouping, or timing; it
is an ancillary linkage gap for this concept.

The ETL omits linkorderid/identifier at
`mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23,38-100`; the source
`orderid` in the opaque UUID is not a recoverable semantic channel. A genuine
upstream timing residual remains: 33 starts, 34 ends, 9 both, 58 unique rows
(0.0173% of 336,000) are shifted by +1 hour. The upstream ETL casts both
endpoints through `TIMESTAMPTZ` at
`mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9` and writes them to
Period start/end at `:61-66`. The original DST-gap wall time is absent from
served FHIR; attempt_0003's `TIMESTAMP_NTZ` mapping correctly preserves the
served value. No second-order row effects occur because this concept has no
time overlay or aggregation.

The judge should rule on the ancillary linkorderid gap and the cited upstream
timestamp transformation. No new dataset-wide note was appended.
