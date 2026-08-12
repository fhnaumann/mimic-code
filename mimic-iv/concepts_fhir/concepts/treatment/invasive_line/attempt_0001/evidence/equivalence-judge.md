# Evidence: equivalence-judge

Concept `invasive_line`, attempt `0001`.

Verdict: `accept` for the `contested` review. The full-data comparison has 93,378 rows on each side, 92,714 identical (99.29%), and 664 residual paired conflicts (0.711%): 657 `line_site`, 7 `starttime`, and 1 `endtime`. The judge verified the upstream citations: `mimic-fhir/sql/fhir_procedure_icu.sql:12,62-69` trims and serializes only the transformed body-site code, losing 555 `Right Antecube ` and 102 `L Ventricular ` source values; lines `10-11,73-76` cast and write both performed Period endpoints through `TIMESTAMPTZ`, irreversibly changing the eight DST-gap endpoint values. No raw location whitespace or pre-cast endpoint is retained elsewhere, and the affected endpoint fraction is consistent with DST-gap rarity. The port used the defensible Procedure mappings and `TIMESTAMP_NTZ` parsing; no retry or carryover invalidation is warranted.

Judge citation: the divergence is upstream MIMIC-on-FHIR transformation loss, not a fixable port bug, so the result should be accepted as `COMPLETED_WITH_DIVERGENCE`.
