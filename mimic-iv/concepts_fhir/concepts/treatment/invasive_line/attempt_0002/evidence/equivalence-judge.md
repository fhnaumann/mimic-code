# Equivalence-judge evidence — invasive_line attempt_0002

- The independent judge reviewed the full comparison, canonical SQL, attempt
  artifacts, curated notes, and diagnostician evidence. There were no
  divergent dependencies and no provisional fragment was cited.
- Verdict: `accept` for the `contested` review.
- The judge found 92,714/93,378 rows identical (99.2889%); all 664 conflicts
  were accounted for as 656 site-only, one site-plus-endtime, and seven
  starttime-only rows. The 657 `line_site` conflicts are caused by
  `mimic-fhir/sql/fhir_procedure_icu.sql:12,62-69`, which trims and serializes
  only normalized `Procedure.bodySite.coding.code`; the source SQL preserves
  raw whitespace and no FHIR element can recover it. This is ancillary
  formatting loss.
- The seven starttime and one overlapping endtime conflicts are the upstream
  Procedure `TIMESTAMPTZ` normalization at
  `mimic-fhir/sql/fhir_procedure_icu.sql:10-11,73-76`; the comparator/source
  replay accounts for them, and the affected fraction is consistent with DST
  rarity. Proven DST normalization is not essential loss under the contract.
- The judge found no remaining mapping fix, no essential loss, and required
  `accept-divergence` with the cited ETL justification.
