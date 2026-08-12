## ICU Procedure resources have no serialized identifier
- Affected: `Procedure.identifier` and recovery of `procedureevents.orderid`
- Verified: invasive_line embedded Pathling probe over the authoritative Delta counted 0/3,450 Procedure resources with an identifier; `/Users/nau025/Documents/mimic-fhir/sql/fhir_procedure_icu.sql:17-19,36-76` derives an opaque UUID from `stay_id-orderid-itemid` but serializes no orderid or identifier.

## Procedure body-site codings carry code/system but no display
- Affected: `Procedure.bodySite.coding.display`
- Verified: invasive_line embedded Pathling probe over the authoritative Delta found 353/353 Procedure body-site codings with non-null `code` and `system` but 0/353 with `display`; the invasive-line target had 140/216 present codings and 0/140 displays.

## ICU Procedure body-site codes are whitespace-trimmed before FHIR serialization
- Affected: `Procedure.bodySite.coding.code` from `procedureevents.location`
- Verified: invasive_line DuckDB/Delta probe found the FHIR body-site multiset exactly matched `TRIM(REGEXP_REPLACE(location, '\\s+', ' ', 'g'))` for 140/140 non-null target rows; four source `Right Antecube ` values therefore appear as `Right Antecube` and cannot be recovered byte-for-byte.
## ICU Procedure body-site codes lose source whitespace
- Affected: Procedure.bodySite.coding.code for the ICU procedureevents-derived Procedure stream.
- Verified: `invasive_line` attempt_0001 full-data comparison paired all 93,378 rows and found exactly 657 `line_site` conflicts: 555 source `Right Antecube ` values became `Right Antecube`, and 102 source `L Ventricular ` values became `L Ventricular`. Upstream `mimic-fhir/sql/fhir_procedure_icu.sql:12` applies `TRIM(REGEXP_REPLACE(pe.location, '\s+', ' ', 'g'))`, and lines 62-69 write only that transformed value to `Procedure.bodySite.coding.code`; no other Procedure element preserves raw `procedureevents.location`.

## ICU Procedure performed Period endpoints lose DST-gap wall times
- Affected: Procedure.performed.ofType(Period).start and Procedure.performed.ofType(Period).end for the ICU procedureevents-derived Procedure stream.
- Verified: `invasive_line` attempt_0001 full-data comparison found 7 `starttime` and 1 `endtime` conflicts, each candidate value exactly one hour later than the oracle in an America/New_York spring-forward gap. The comparator replayed and attributed all 7 start conflicts; independent residual inspection identified the end conflict as oracle `2186-03-12 02:30:00` versus FHIR `03:30:00`. Upstream `mimic-fhir/sql/fhir_procedure_icu.sql:10-11` casts both naive source endpoints to `TIMESTAMPTZ`, and lines 73-76 write only the cast values to `performedPeriod`, so the original nonexistent wall time is unrecoverable.
