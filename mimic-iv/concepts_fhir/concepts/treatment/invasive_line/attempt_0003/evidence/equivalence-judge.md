# Equivalence judge evidence

- Concept: `invasive_line`; attempt `0003`.
- Verdict: `accept` for the `contested` / `paired_residual` review.
- Full data: 93,378 candidate and oracle rows; 92,721 identical and 657 `differing_conflict` rows (0.704%), exclusively on `line_site`; zero only-oracle, only-candidate, or differing-null rows.
- Citation: canonical `invasive_line.sql:10,90-127` preserves source location, while `mimic-fhir/sql/fhir_procedure_icu.sql:12` applies `TRIM(REGEXP_REPLACE(pe.location, '\\s+', ' ', 'g'))` and lines `62-69` serialize only the normalized value to `Procedure.bodySite.coding.code`.
- The raw whitespace is unrecoverable by any FHIR query because the many-to-one normalization stores no untrimmed copy; resource identity is opaque and cannot be used for recovery.
- The divergence is ancillary formatting loss: anatomical meaning, inclusion, grain, multiplicity, grouping, timing, and clinical derivations are unchanged.
- Terminal outcome: `COMPLETED_WITH_DIVERGENCE`.
