# Equivalence judge evidence

Verdict: `accept` for the `review` / `contested` result.

The diff is VOID DIFF because declared-unrepresentable `linkorderid` is part of
the manifest key `(linkorderid,starttime)`. The symmetric 336,000
`only_oracle` / `only_candidate` counts are alignment artifacts; there are no
`differing_conflict` or `differing_null_only` rows. A focused representable
multiset comparison reproduced all 336,000 rows and multiplicities.

`MedicationAdministration.identifier` and `supportingInformation` do not carry
`inputevents.linkorderid`. The ICU ETL emits one resource per inputevent but
omits that linkage (`mimic-fhir/sql/fhir_medication_administration_icu.sql:1,7-23,24-35,38-100`);
`orderid` at line 20 is only in an opaque UUID and cannot be inverted. The
canonical query only projects this administrative field and has no joins,
grouping, aggregation, or deduplication (`mimic-iv/concepts/medication/norepinephrine.sql:3-16`),
so the loss is ancillary rather than essential.

The UTC rebuild removed attempt_0003's 58 timing residuals; attempt_0004 has no
actual DST residual. No new dataset-wide quirk was found and no retry is
warranted.
