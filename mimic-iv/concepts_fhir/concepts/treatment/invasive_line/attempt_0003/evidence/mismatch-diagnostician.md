# Divergence diagnosis evidence

- Concept: `invasive_line`; attempt `0003`.
- Diagnosis: upstream transformation loss, not a port bug.
- The canonical SQL preserves source `procedureevents.location` whitespace, while `mimic-fhir/sql/fhir_procedure_icu.sql:12` applies `TRIM(REGEXP_REPLACE(pe.location, '\\s+', ' ', 'g'))`; lines `62-69` serialize only the transformed value as `Procedure.bodySite.coding.code`.
- The FHIR representation carries no raw location, alternate display/text, extension, or identifier preserving the discarded whitespace, so no FHIR query can recover it.
- The full diff contains 657 `line_site` conflicts only, with 92,721/93,378 rows identical and no missing or invented rows. The loss is ancillary formatting and does not alter grain, inclusion, multiplicity, grouping, identifiers, or timing.
- Recommended route: judge review acceptance; no SQL/ViewDefinition change and no carryover invalidation.
- The diagnostician reported appending a rebuilt-warehouse re-verification to `MIMIC_NOTES.d/invasive_line.md`.
