# Mismatch-diagnostician evidence — invasive_line attempt_0002

- Read the loop contract, curated `MIMIC_NOTES.md`, canonical
  `invasive_line.sql`, attempt ViewDefinitions/SQL, comparison and run
  metadata, the reusable analyses, the oracle-manifest entry, and
  `/Users/nau025/Documents/mimic-fhir/sql/fhir_procedure_icu.sql`. No
  provisional fragment was cited as evidence.
- Diagnosed the contested residual as upstream transformation loss, not a
  candidate bug. The canonical SQL preserves whitespace in
  `procedureevents.location` (`invasive_line.sql:10,90-127`), while the ETL
  computes `TRIM(REGEXP_REPLACE(pe.location, '\\s+', ' ', 'g'))` at
  `mimic-fhir/sql/fhir_procedure_icu.sql:12` and serializes only the normalized
  value at `:62-69` as `Procedure.bodySite.coding.code`.
- Exhaustive source-side accounting closed the 664 conflicts: 657 site
  changes, seven already-attributed starttime DST shifts, and one endtime DST
  shift overlapping one site change. The site residual is 656 site-only plus
  one site-and-endtime row; all 657 are explained by lost whitespace.
- The served Procedure has no raw location, display/text, extension, or
  identifier preserving the original value. Padding or parsing opaque ids
  would be an estimate or forbidden side channel, so the oracle whitespace is
  unrecoverable by any FHIR query. No carryover invalidation or implementation
  change is recommended; route the complete review to the judge.
