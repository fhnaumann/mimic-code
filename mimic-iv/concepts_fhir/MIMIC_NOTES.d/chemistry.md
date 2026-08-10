## Lab Specimen.type coding has no display
- Affected: `Specimen.type.coding.display` for the lab-specimen stream
- Verified: chemistry Delta probe over 11,122 `specimen-lab` resources found `display` non-null on 0/11,122; `mimic-fhir/sql/fhir_specimen_lab.sql:50-54` writes the fluid code and system but no display.

## Spark SQL doubled-quote datetime patterns lose the literal `T`
- Affected: `TRY_TO_TIMESTAMP` format strings for ISO FHIR datetimes in Spark SQL
- Verified: chemistry attempt_0001 demo execution rejected `yyyy-MM-dd''T''HH:mm:ss` with `Unknown pattern letter: T`; attempt_0002 demo succeeded after stripping the offset and replacing `T` with a space before `TRY_TO_TIMESTAMP(..., 'yyyy-MM-dd HH:mm:ss')`, with `TRY_CAST(... AS TIMESTAMP_NTZ)` retaining the normal path.

## Do not COALESCE FHIR dateTime strings with a Pathling instant before casting
- Affected: `Observation.effective[x]` ViewDefinition aliases, especially `effective.ofType(dateTime)`, `effective.ofType(Period).start`, and `effective.ofType(instant)`
- Verified: `chemistry` attempt_0002 had 3,811,523/3,811,523 keyed `differing_conflict` rows solely on `charttime`, with equal row counts and every other column matching. Pathling 9.6.0 materialized the first two aliases as STRING but the instant alias as TIMESTAMP; Spark therefore typed their `COALESCE` as TIMESTAMP and offset-normalized the dateTime string before the later `TIMESTAMP_NTZ` cast, producing 1416 hour shifts. The same attempt's 3,289 demo rows had zero exact charttimes and 1416 hour deltas. Cast/coalesce only the string variants for labevents, whose ETL writes `effectiveDateTime`, and omit the unused instant alias.

## Correction: the effective-time coercion shifts are 14 to 16 hours
- Affected: `Observation.effective[x]` ViewDefinition aliases, especially mixed STRING `dateTime`/`Period.start` and TIMESTAMP `instant` aliases
- Verified: `chemistry` attempt_0002 and the same 3,811,523 full-data conflicts establish shifts of 14, 15, or 16 hours; this corrects only the malformed range typography in the immediately preceding append-only entry, not its claim or diagnosis.
