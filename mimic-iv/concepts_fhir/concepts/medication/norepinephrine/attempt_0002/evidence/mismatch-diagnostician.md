# Mismatch diagnosis — norepinephrine attempt_0002

The comparator's 336,000 `only_oracle` and 336,000 `only_candidate` rows are a
VOID-DIFF artifact: declared-unrepresentable `linkorderid` is part of the
manifest key `(linkorderid, starttime)`, so no keyed rows can align. Equal row
counts do not repair that comparison metadata issue.

The diagnostician nevertheless found a separate fixable semantic bug in
`concept.sql:37-42`: attempt_0002 emitted NULL for every `mg/kg/min` rate. A
full-oracle probe found exactly two such norepinephrine rows, both with
`patientweight=1`, so the canonical branch requires the raw rate for both.
The missing patientweight is therefore not an exercised loss for these rows.
The fix is to restore the unconditional raw FHIR rate cast for `vaso_rate`; no
carryover stage is at fault and no ViewDefinition change is needed.

The remaining issues after that fix are semantic evidence for the judge, not
this attempt's terminal decision: `linkorderid` is absent from the served ICU
MedicationAdministration ETL (`mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23,38-100`),
and 58 rows have irreversible endpoint normalization from the ETL's
`TIMESTAMPTZ` cast and Period writes
(`mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-69`).
The original linkorderid and DST-gap wall times are not recoverable from served
FHIR; resource IDs remain opaque.

The required action is a semantic fail and a fresh immutable retry. No
carryover invalidation is required. No dataset-wide note was appended by this
diagnosis.
